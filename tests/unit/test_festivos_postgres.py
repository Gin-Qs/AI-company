"""Los festivos de Postgres, y que de verdad muevan el reloj del SLA.

"Es configurable" es facil de afirmar y dificil de comprobar. Un archivo de politica que el
codigo carga pero ignora se ve igual que uno que respeta, hasta el dia que alguien cambia un
numero y no pasa nada. Aqui se cambia el dato y se exige que el comportamiento cambie.

Ninguna prueba abre una conexion: se sustituye el lector. Lo que se comprueba es la decision
de que fuente usar, el fallo cuando no se puede leer, y —sobre todo— que un feriado declarado
alargue el vencimiento.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from services.common.postgres import BaseIlegible
from services.runlog import festivos as festivos_pg
from services.runlog import sla


@pytest.fixture(autouse=True)
def sin_base(monkeypatch):
    monkeypatch.delenv("DIRECT_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sla.cargar_calendario.cache_clear()
    yield
    sla.cargar_calendario.cache_clear()


def _con_festivos(monkeypatch, fechas: set[date]) -> None:
    """Simula una base configurada que responde con estos festivos."""
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setattr(festivos_pg, "fechas", lambda cadena=None: frozenset(fechas))


# --- de donde salen ---------------------------------------------------------


def test_sin_base_el_calendario_es_el_del_yaml():
    vigente = sla.calendario_vigente()
    assert vigente.festivos == sla.cargar_calendario().festivos


def test_con_base_se_suman_los_declarados(monkeypatch):
    _con_festivos(monkeypatch, {date(2026, 9, 16)})
    assert date(2026, 9, 16) in sla.calendario_vigente().festivos


def test_no_se_pierde_lo_que_ya_estaba_en_el_yaml(monkeypatch, tmp_path):
    """Union, no reemplazo. Que la fuente se haya movido no invalida lo ya declarado."""
    archivo = tmp_path / "calendario-laboral.yaml"
    archivo.write_text(
        "version: v1\ncalibrado: parcial\n"
        "huso: {offset_horas: -6, nombre: local}\n"
        "jornada: {apertura: '09:00', cierre: '18:00', dias_habiles: [0,1,2,3,4]}\n"
        "festivos: {fechas: ['2026-12-25']}\n",
        encoding="utf-8",
    )
    _con_festivos(monkeypatch, {date(2026, 9, 16)})
    vigente = sla.calendario_vigente(str(archivo))
    assert date(2026, 12, 25) in vigente.festivos  # del YAML
    assert date(2026, 9, 16) in vigente.festivos   # de Postgres


# --- LA PRUEBA QUE IMPORTA: el dato mueve el reloj --------------------------


# Martes 15 de septiembre de 2026, 16:00 en CDMX (22:00 UTC). La hora importa: el SLA de
# criticidad alta son 4 horas habiles y la jornada cierra a las 18:00, asi que arrancando a
# las 16:00 solo caben dos — las otras dos caen al dia siguiente. Arrancar por la mañana
# haria que el plazo cupiera entero ese dia y el festivo del 16 no cambiaria nada, y la
# prueba pasaria sin comprobar lo que dice comprobar.
VISPERA = datetime(2026, 9, 15, 22, 0, tzinfo=timezone.utc)


def test_un_festivo_declarado_corre_el_vencimiento(monkeypatch):
    """El 16 de septiembre es miercoles en 2026. Declararlo tiene que empujar el vencimiento
    al jueves — si no, el dato esta guardado y nadie lo usa."""
    desde = VISPERA

    sin_declarar = sla.vencimiento(desde, "alta")
    _con_festivos(monkeypatch, {date(2026, 9, 16)})
    con_declarado = sla.vencimiento(desde, "alta")

    assert con_declarado > sin_declarar, (
        "declarar el 16 de septiembre no cambio el vencimiento: el festivo se guarda y el "
        "reloj lo ignora"
    )
    # Y no cae en el dia declarado.
    assert con_declarado.astimezone(sla.HUSO).date() != date(2026, 9, 16)


def test_quitar_el_festivo_devuelve_el_vencimiento_original(monkeypatch):
    """La otra mitad: si solo se comprobara que declarar alarga, un calendario que siempre
    alargara pasaria la prueba."""
    desde = VISPERA
    original = sla.vencimiento(desde, "alta")

    _con_festivos(monkeypatch, {date(2026, 9, 16)})
    assert sla.vencimiento(desde, "alta") != original

    monkeypatch.setattr(festivos_pg, "fechas", lambda cadena=None: frozenset())
    assert sla.vencimiento(desde, "alta") == original


def test_un_festivo_en_otra_fecha_no_mueve_nada(monkeypatch):
    """Un calendario que alargara con cualquier dato seria indistinguible de uno correcto."""
    desde = VISPERA
    original = sla.vencimiento(desde, "alta")
    _con_festivos(monkeypatch, {date(2027, 3, 1)})
    assert sla.vencimiento(desde, "alta") == original


def test_el_festivo_tambien_cuenta_para_resolver_vencimiento(monkeypatch):
    """`resolver_vencimiento` decide si un HITL ya vencio. Si ignorara los festivos,
    escalaria casos en un dia en que nadie podia atenderlos."""
    espera = VISPERA
    # Un dia despues: sin festivos el caso ya habria vencido (vence el 16 a las 11:00 CDMX).
    ahora = espera + timedelta(hours=24)

    _con_festivos(monkeypatch, {date(2026, 9, 16), date(2026, 9, 17), date(2026, 9, 18)})
    assert (
        sla.resolver_vencimiento(
            trace_id="TR-X", criticidad="alta", espera_desde=espera, ahora=ahora
        )
        is None
    ), "el caso se dio por vencido durante tres dias declarados feriados"


# --- cuando no se puede leer ------------------------------------------------


def test_si_la_base_no_responde_el_sla_no_se_calcula(monkeypatch):
    """Una lista de festivos vacia no es un error visible: es un calendario que afirma que se
    trabaja todos los dias, y el SLA vence antes. Se propaga el error."""
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host:5432/db")

    def truena(cadena=None):
        raise BaseIlegible("no se pudo leer la lista de festivos de Postgres")

    monkeypatch.setattr(festivos_pg, "fechas", truena)
    with pytest.raises(BaseIlegible):
        sla.calendario_vigente()


def test_un_marcador_de_contrasena_cuenta_como_sin_base(monkeypatch):
    monkeypatch.setenv("DIRECT_URL", "postgresql://postgres:CONTRASENA@host:5432/db")
    # No debe intentar leer: cae al YAML sin tocar la red.
    def no_deberia_llamarse(cadena=None):  # pragma: no cover
        raise AssertionError("intento leer Postgres con un marcador de contrasena")

    monkeypatch.setattr(festivos_pg, "fechas", no_deberia_llamarse)
    assert sla.calendario_vigente().festivos == sla.cargar_calendario().festivos


# --- el modulo compartido ---------------------------------------------------


def test_consultar_sin_base_configurada_dice_que_se_perdio():
    from services.common.postgres import consultar

    with pytest.raises(BaseIlegible) as fallo:
        consultar("select 1", que="los festivos de prueba")
    assert "los festivos de prueba" in str(fallo.value)
