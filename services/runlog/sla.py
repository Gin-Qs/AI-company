"""SLA y regla dura de timeout (§7.3).

    Un HITL vencido escala o expira. Nunca auto-aprueba.

Toda la aritmetica es de horas habiles, porque un SLA de 4 horas que corre un sabado a las
once de la noche no es un SLA: es una trampa.

DE DONDE SALEN LOS NUMEROS. De ningun lugar de este archivo. Hasta v3.0.1 la jornada y los
plazos estaban aqui en duro, y `authority-gate.yaml` declaraba los mismos plazos sin que
nadie los leyera: cambiar el SLA en la politica no cambiaba nada. Ahora hay una sola fuente
por cosa, y este modulo la consume:

    registry/policies/calendario-laboral.yaml   huso, jornada, dias habiles, festivos
    registry/policies/authority-gate.yaml       hitl.sla: plazo y consecuencia por criticidad

Cambiar un horario o un plazo es editar un YAML y abrir un PR. No se toca este archivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from services.common.errors import ErrorDeValidacion

RAIZ = Path(__file__).resolve().parent.parent.parent
CALENDARIO = RAIZ / "registry" / "policies" / "calendario-laboral.yaml"
GATE = RAIZ / "registry" / "policies" / "authority-gate.yaml"

ACCIONES = ("escalar", "expirar", "bloquear")


class NuncaAutoAprueba(AssertionError):
    """Se intento resolver un vencimiento aprobando. Es la unica salida prohibida.

    Se levanta al CARGAR la politica, no al aplicarla. Un `al_vencer: aprobar` escrito en
    el YAML tiene que reventar el arranque, no descubrirse el dia que un HITL vence.
    """


# --- la politica, cargada -------------------------------------------------


@dataclass(frozen=True)
class Calendario:
    """El horario de oficina declarado en calendario-laboral.yaml."""

    huso: timezone
    apertura: time
    cierre: time
    dias_habiles: tuple[int, ...]
    festivos: frozenset[date]
    calibrado: str = "parcial"
    version: str = "v1"

    @property
    def horas_por_dia(self) -> float:
        """Un dia habil dura lo que dure la jornada. No se supone: se resta."""
        abre = self.apertura.hour + self.apertura.minute / 60
        cierra = self.cierre.hour + self.cierre.minute / 60
        return cierra - abre


def _hora(texto: object, campo: str) -> time:
    try:
        return time.fromisoformat(str(texto))
    except ValueError as exc:
        raise ErrorDeValidacion(f"{campo} no es una hora valida: {texto!r}", campo=campo) from exc


@lru_cache(maxsize=8)
def cargar_calendario(ruta: str | None = None) -> Calendario:
    destino = Path(ruta) if ruta else CALENDARIO
    if not destino.is_file():
        raise ErrorDeValidacion(f"no existe el calendario laboral: {destino}", campo="calendario")
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}

    huso_cfg = datos.get("huso") or {}
    jornada = datos.get("jornada") or {}
    festivos_cfg = datos.get("festivos") or {}

    apertura = _hora(jornada.get("apertura", "09:00"), "apertura")
    cierre = _hora(jornada.get("cierre", "18:00"), "cierre")
    if apertura >= cierre:
        raise ErrorDeValidacion(
            f"la jornada abre a las {apertura} y cierra a las {cierre}: nunca avanzaria el reloj",
            campo="jornada",
        )

    # `or` no sirve aqui: una lista vacia es falsy y quedaria convertida en el valor
    # por defecto. "No lo declare" y "declare que no hay ninguno" no son lo mismo.
    declarados = jornada.get("dias_habiles")
    dias = tuple(int(d) for d in (declarados if declarados is not None else [0, 1, 2, 3, 4]))
    if not dias:
        raise ErrorDeValidacion("no hay ni un dia habil: ningun SLA podria vencer", campo="dias_habiles")
    if any(d < 0 or d > 6 for d in dias):
        raise ErrorDeValidacion(f"dia habil fuera de rango 0-6: {dias}", campo="dias_habiles")

    # PyYAML ya convierte `2026-09-16` en un date. Un texto tambien se acepta, porque el
    # dia que alguien pegue la lista entre comillas no tiene por que fallar en silencio.
    festivos = frozenset(
        f if isinstance(f, date) else date.fromisoformat(str(f))
        for f in (festivos_cfg.get("fechas") or [])
    )

    offset = float(huso_cfg.get("offset_horas", -6))
    return Calendario(
        huso=timezone(timedelta(hours=offset), str(huso_cfg.get("nombre") or "local")),
        apertura=apertura,
        cierre=cierre,
        dias_habiles=dias,
        festivos=festivos,
        calibrado=str(datos.get("calibrado") or "parcial"),
        version=str(datos.get("version") or "v1"),
    )


@dataclass(frozen=True)
class ReglaSLA:
    criticidad: str
    al_vencer: str
    luego: str
    horas_habiles: float | None = None
    dias_habiles: int | None = None
    resumen: str = ""

    def horas(self, calendario: Calendario) -> float:
        if self.horas_habiles is not None:
            return self.horas_habiles
        return (self.dias_habiles or 0) * calendario.horas_por_dia


@lru_cache(maxsize=8)
def cargar_sla(ruta: str | None = None) -> dict[str, ReglaSLA]:
    """Los plazos de §7.3, leidos de authority-gate.yaml -> hitl.sla."""
    destino = Path(ruta) if ruta else GATE
    if not destino.is_file():
        raise ErrorDeValidacion(f"no existe el gate de autoridad: {destino}", campo="gate")
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    crudo = ((datos.get("hitl") or {}).get("sla")) or {}
    if not crudo:
        raise ErrorDeValidacion("authority-gate.yaml no declara hitl.sla", campo="sla")

    reglas: dict[str, ReglaSLA] = {}
    for criticidad, regla in crudo.items():
        al_vencer = str(regla.get("al_vencer") or "")
        luego = str(regla.get("luego") or al_vencer)

        # La regla dura, impuesta donde se escribe la politica y no donde se aplica.
        for accion in (al_vencer, luego):
            if accion not in ACCIONES:
                raise NuncaAutoAprueba(
                    f"hitl.sla.{criticidad} declara {accion!r}, que no es una consecuencia "
                    f"permitida. Un HITL vencido escala o expira; nunca auto-aprueba (§7.3). "
                    f"Validas: {', '.join(ACCIONES)}"
                )

        if regla.get("horas_habiles") is None and regla.get("dias_habiles") is None:
            raise ErrorDeValidacion(
                f"hitl.sla.{criticidad} no declara plazo: falta horas_habiles o dias_habiles",
                campo="sla",
            )

        reglas[str(criticidad)] = ReglaSLA(
            criticidad=str(criticidad),
            al_vencer=al_vencer,
            luego=luego,
            horas_habiles=regla.get("horas_habiles"),
            dias_habiles=regla.get("dias_habiles"),
            resumen=str(regla.get("resumen") or ""),
        )
    return reglas


# --- constantes de compatibilidad ------------------------------------------
# El resto del sistema y las pruebas importan estos nombres. Siguen existiendo, pero ya
# no son la declaracion: son el resultado de leer la politica.

_CAL = cargar_calendario()

HUSO = _CAL.huso
APERTURA = _CAL.apertura
CIERRE = _CAL.cierre
DIAS_HABILES = _CAL.dias_habiles
HORAS_POR_DIA = _CAL.horas_por_dia

#: §7.3 tal como queda tras leer authority-gate.yaml. Se conserva la forma de diccionario
#: que tenia cuando estaba en duro, para no romper a quien ya la importaba.
SLA = {
    criticidad: {
        **({"horas_habiles": r.horas_habiles} if r.horas_habiles is not None else {}),
        **({"dias_habiles": r.dias_habiles} if r.dias_habiles is not None else {}),
        "al_vencer": r.al_vencer,
        "luego": r.luego,
    }
    for criticidad, r in cargar_sla().items()
}


# --- aritmetica del calendario ---------------------------------------------


def a_local(momento: datetime, calendario: Calendario | None = None) -> datetime:
    """Lleva cualquier momento a la hora de oficina. Un naive se asume ya local."""
    cal = calendario or _CAL
    if momento.tzinfo is None:
        return momento.replace(tzinfo=cal.huso)
    return momento.astimezone(cal.huso)


def _es_dia_habil(momento: datetime, cal: Calendario) -> bool:
    """Lunes a viernes y que no sea festivo. Un festivo cuenta igual que un sabado."""
    return momento.weekday() in cal.dias_habiles and momento.date() not in cal.festivos


def es_habil(momento: datetime, calendario: Calendario | None = None) -> bool:
    cal = calendario or _CAL
    local = a_local(momento, cal)
    return _es_dia_habil(local, cal) and cal.apertura <= local.time() < cal.cierre


def _siguiente_apertura(momento: datetime, cal: Calendario) -> datetime:
    candidato = momento
    if candidato.time() >= cal.cierre:
        candidato = (candidato + timedelta(days=1)).replace(
            hour=cal.apertura.hour, minute=cal.apertura.minute, second=0, microsecond=0
        )
    elif candidato.time() < cal.apertura:
        candidato = candidato.replace(
            hour=cal.apertura.hour, minute=cal.apertura.minute, second=0, microsecond=0
        )
    # Un instante dentro de la jornada pero en sabado —o en festivo— no entra en ninguna
    # rama de arriba: lo mueve este bucle.
    while not _es_dia_habil(candidato, cal):
        candidato = (candidato + timedelta(days=1)).replace(
            hour=cal.apertura.hour, minute=cal.apertura.minute, second=0, microsecond=0
        )
    return candidato


def sumar_horas_habiles(desde: datetime, horas: float, calendario: Calendario | None = None) -> datetime:
    """Avanza `horas` de reloj laboral desde un momento cualquiera."""
    cal = calendario or _CAL
    if horas < 0:
        raise ErrorDeValidacion("no se puede sumar un SLA negativo", campo="horas")
    original = desde.tzinfo or cal.huso
    momento = _siguiente_apertura(a_local(desde, cal), cal)
    restante = timedelta(hours=horas)

    while restante > timedelta(0):
        fin_del_dia = momento.replace(
            hour=cal.cierre.hour, minute=cal.cierre.minute, second=0, microsecond=0
        )
        disponible = fin_del_dia - momento
        if restante <= disponible:
            return (momento + restante).astimezone(original)
        restante -= disponible
        momento = _siguiente_apertura(fin_del_dia, cal)
    return momento.astimezone(original)


def sumar_dias_habiles(desde: datetime, dias: int, calendario: Calendario | None = None) -> datetime:
    cal = calendario or _CAL
    return sumar_horas_habiles(desde, dias * cal.horas_por_dia, cal)


def vencimiento(desde: datetime, criticidad: str, calendario: Calendario | None = None) -> datetime:
    cal = calendario or _CAL
    reglas = cargar_sla()
    if criticidad not in reglas:
        raise ErrorDeValidacion(f"criticidad desconocida: {criticidad!r}", campo="criticidad")
    return sumar_horas_habiles(desde, reglas[criticidad].horas(cal), cal)


@dataclass(frozen=True)
class Vencimiento:
    trace_id: str
    criticidad: str
    vence_en: str
    accion: Literal["escalar", "expirar", "bloquear"]
    escalamientos_previos: int
    motivo: str

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "criticidad": self.criticidad,
            "vence_en": self.vence_en,
            "accion": self.accion,
            "escalamientos_previos": self.escalamientos_previos,
            "motivo": self.motivo,
        }


def resolver_vencimiento(
    *,
    trace_id: str,
    criticidad: str,
    espera_desde: datetime,
    ahora: datetime,
    escalamientos: int = 0,
    calendario: Calendario | None = None,
) -> Vencimiento | None:
    """Que hacer con un HITL que espera. `None` si todavia no vence.

    La salida nunca es "aprobar" — por eso la funcion no tiene ese caso ni puede tenerlo.
    Con la politica por defecto: alta escala y deja el caso bloqueado; media escala una vez
    y luego expira; baja expira.
    """
    cal = calendario or _CAL
    reglas = cargar_sla()
    if criticidad not in reglas:
        raise ErrorDeValidacion(f"criticidad desconocida: {criticidad!r}", campo="criticidad")

    limite = vencimiento(espera_desde, criticidad, cal)
    if ahora < limite:
        return None

    regla = reglas[criticidad]
    accion = regla.al_vencer if escalamientos == 0 else regla.luego
    motivos = {
        "escalar": "vencio el SLA: escala al siguiente nivel",
        "expirar": "vencio y ya se habia escalado: expira y se cierra como no_atendido"
        if escalamientos
        else "vencio el SLA de criticidad baja: expira y se cierra como no_atendido",
        "bloquear": "vencio despues de escalar: el caso queda bloqueado hasta que una persona lo resuelva",
    }

    if accion not in ACCIONES:
        raise NuncaAutoAprueba(f"accion invalida al vencer: {accion!r}")

    return Vencimiento(
        trace_id=trace_id,
        criticidad=criticidad,
        vence_en=limite.isoformat(timespec="seconds"),
        accion=accion,
        escalamientos_previos=escalamientos,
        motivo=motivos[accion],
    )
