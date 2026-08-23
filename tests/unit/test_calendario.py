"""El calendario laboral y el SLA se configuran desde YAML, no desde el codigo.

Estas pruebas existen porque "es configurable" es una afirmacion facil de hacer y dificil
de comprobar. Un archivo de politica que el codigo carga pero ignora se ve exactamente
igual que uno que respeta — hasta el dia que alguien cambia un numero y no pasa nada.

Cada prueba de aqui cambia una linea del YAML y exige que el comportamiento cambie.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from services.common.errors import ErrorDeValidacion
from services.runlog.sla import (
    NuncaAutoAprueba,
    cargar_calendario,
    cargar_sla,
    resolver_vencimiento,
    sumar_horas_habiles,
    vencimiento,
)

CALENDARIO_BASE = """
version: v-prueba
calibrado: parcial
huso:
  offset_horas: -6
  nombre: CST-MX
jornada:
  apertura: "09:00"
  cierre: "18:00"
  dias_habiles: [0, 1, 2, 3, 4]
festivos:
  calibrado: false
  fechas: [{festivos}]
"""

GATE_BASE = """
hitl:
  sla:
    alta:  {{ horas_habiles: {horas_alta}, al_vencer: {al_vencer}, luego: bloquear }}
    media: {{ dias_habiles: 1, al_vencer: escalar, luego: expirar }}
    baja:  {{ dias_habiles: 3, al_vencer: expirar, luego: expirar }}
"""


def _calendario(tmp_path, *, festivos: str = "", jornada: tuple[str, str] | None = None):
    texto = CALENDARIO_BASE.format(festivos=festivos)
    if jornada:
        texto = texto.replace('apertura: "09:00"', f'apertura: "{jornada[0]}"')
        texto = texto.replace('cierre: "18:00"', f'cierre: "{jornada[1]}"')
    tmp_path.mkdir(parents=True, exist_ok=True)
    ruta = tmp_path / "calendario.yaml"
    ruta.write_text(texto, encoding="utf-8")
    return cargar_calendario(str(ruta))


def _gate(tmp_path, *, horas_alta: int = 4, al_vencer: str = "escalar"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    ruta = tmp_path / "gate.yaml"
    ruta.write_text(GATE_BASE.format(horas_alta=horas_alta, al_vencer=al_vencer), encoding="utf-8")
    return ruta


# --- festivos ---------------------------------------------------------------


def test_un_festivo_no_cuenta_para_el_reloj(tmp_path):
    """Un festivo se salta igual que un sabado. Es el caso del 16 de septiembre."""
    cal = _calendario(tmp_path, festivos="2026-09-16")

    # Martes 15 de septiembre, 16:00 local. Quedan 2h de jornada; faltarian 2h mas.
    martes = datetime(2026, 9, 15, 16, 0, tzinfo=cal.huso)
    vence = sumar_horas_habiles(martes, 4, cal)

    # El miercoles 16 es feriado: las 2h restantes caen el jueves 17 por la mañana.
    assert vence == datetime(2026, 9, 17, 11, 0, tzinfo=cal.huso)


def test_sin_festivos_el_mismo_caso_vence_un_dia_antes(tmp_path):
    """La contraprueba: si la lista esta vacia, el 16 es un dia habil normal."""
    cal = _calendario(tmp_path, festivos="")

    martes = datetime(2026, 9, 15, 16, 0, tzinfo=cal.huso)
    assert sumar_horas_habiles(martes, 4, cal) == datetime(2026, 9, 16, 11, 0, tzinfo=cal.huso)


def test_un_festivo_en_viernes_empuja_al_lunes(tmp_path):
    cal = _calendario(tmp_path, festivos="2026-09-18")

    jueves = datetime(2026, 9, 17, 17, 0, tzinfo=cal.huso)   # queda 1h de jornada
    vence = sumar_horas_habiles(jueves, 3, cal)

    # Viernes feriado y fin de semana: las 2h restantes caen el lunes 21.
    assert vence == datetime(2026, 9, 21, 11, 0, tzinfo=cal.huso)


# --- jornada ----------------------------------------------------------------


def test_cambiar_la_jornada_cambia_cuanto_dura_un_dia_habil(tmp_path):
    """`dias_habiles: 1` no son 24 horas ni 9 fijas: son lo que dure la jornada."""
    corta = _calendario(tmp_path / "a", jornada=("09:00", "18:00"))
    larga = _calendario(tmp_path / "b", jornada=("08:00", "20:00"))

    assert corta.horas_por_dia == 9
    assert larga.horas_por_dia == 12


def test_una_jornada_mas_larga_hace_que_el_sla_venza_antes(tmp_path):
    """Mas horas de oficina al dia = el mismo plazo se consume en menos dias."""
    corta = _calendario(tmp_path / "a", jornada=("09:00", "18:00"))
    larga = _calendario(tmp_path / "b", jornada=("08:00", "20:00"))

    lunes_corta = datetime(2026, 6, 1, 16, 0, tzinfo=corta.huso)
    lunes_larga = datetime(2026, 6, 1, 16, 0, tzinfo=larga.huso)

    assert sumar_horas_habiles(lunes_corta, 6, corta) > sumar_horas_habiles(lunes_larga, 6, larga)


def test_una_jornada_imposible_no_se_carga(tmp_path):
    """Si cierra antes de abrir, el reloj nunca avanzaria: se detiene al cargar."""
    ruta = tmp_path / "calendario.yaml"
    ruta.write_text(
        CALENDARIO_BASE.format(festivos="").replace('cierre: "18:00"', 'cierre: "08:00"'),
        encoding="utf-8",
    )
    with pytest.raises(ErrorDeValidacion, match="nunca avanzaria"):
        cargar_calendario(str(ruta))


def test_sin_dias_habiles_no_se_carga(tmp_path):
    ruta = tmp_path / "calendario.yaml"
    ruta.write_text(
        CALENDARIO_BASE.format(festivos="").replace("dias_habiles: [0, 1, 2, 3, 4]", "dias_habiles: []"),
        encoding="utf-8",
    )
    with pytest.raises(ErrorDeValidacion, match="ni un dia habil"):
        cargar_calendario(str(ruta))


# --- los plazos, desde authority-gate.yaml ---------------------------------


def test_cambiar_el_plazo_en_la_politica_cambia_el_vencimiento(tmp_path, monkeypatch):
    """El numero que manda es el del YAML. Antes de v3.0.2 este cambio no hacia nada."""
    cal = _calendario(tmp_path, festivos="")
    lunes = datetime(2026, 6, 1, 10, 0, tzinfo=cal.huso)

    monkeypatch.setattr("services.runlog.sla.GATE", _gate(tmp_path / "a", horas_alta=4))
    cargar_sla.cache_clear()
    assert vencimiento(lunes, "alta", cal) == datetime(2026, 6, 1, 14, 0, tzinfo=cal.huso)

    monkeypatch.setattr("services.runlog.sla.GATE", _gate(tmp_path / "b", horas_alta=6))
    cargar_sla.cache_clear()
    assert vencimiento(lunes, "alta", cal) == datetime(2026, 6, 1, 16, 0, tzinfo=cal.huso)

    cargar_sla.cache_clear()


# --- la regla dura ----------------------------------------------------------


def test_una_politica_que_auto_aprueba_no_se_carga(tmp_path, monkeypatch):
    """§7.3: un HITL vencido escala o expira. Nunca auto-aprueba.

    La regla se impone donde se ESCRIBE la politica, no donde se aplica: un
    `al_vencer: aprobar` tiene que reventar al cargar, no descubrirse el dia que un pago
    de doscientos mil pesos se aprueba solo porque nadie lo miro a tiempo.
    """
    monkeypatch.setattr("services.runlog.sla.GATE", _gate(tmp_path, al_vencer="aprobar"))
    cargar_sla.cache_clear()

    with pytest.raises(NuncaAutoAprueba, match="nunca auto-aprueba"):
        cargar_sla()

    cargar_sla.cache_clear()


def test_ninguna_consecuencia_de_la_politica_vigente_aprueba():
    """La politica que el repositorio trae hoy, comprobada de verdad."""
    for criticidad, regla in cargar_sla().items():
        assert regla.al_vencer in ("escalar", "expirar", "bloquear"), criticidad
        assert regla.luego in ("escalar", "expirar", "bloquear"), criticidad


def test_un_hitl_que_no_ha_vencido_no_tiene_accion(tmp_path):
    cal = _calendario(tmp_path, festivos="")
    espera = datetime(2026, 6, 1, 10, 0, tzinfo=cal.huso)

    assert (
        resolver_vencimiento(
            trace_id="TR-1",
            criticidad="alta",
            espera_desde=espera,
            ahora=datetime(2026, 6, 1, 11, 0, tzinfo=cal.huso),
            calendario=cal,
        )
        is None
    )


# --- trazabilidad -----------------------------------------------------------


def test_el_calendario_declara_si_esta_calibrado():
    """El portal tiene que poder decir 'esto todavia no esta confirmado' (docs/portal.md §14).

    Los festivos siguen sin cargar, y eso tiene consecuencia real. Mientras la lista este
    vacia, esta prueba lo deja escrito en un sitio que se ejecuta.
    """
    cal = cargar_calendario()
    assert cal.calibrado == "parcial"
    assert cal.festivos == frozenset(), "si ya cargaste los festivos, actualiza esta prueba"
