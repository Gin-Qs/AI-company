"""SLA y regla dura de timeout (§7.3).

    Un HITL vencido escala o expira. Nunca auto-aprueba.

Toda la aritmetica es de horas habiles, porque un SLA de 4 horas que corre un sabado a las
once de la noche no es un SLA: es una trampa. El calendario laboral vive aqui, en un solo
lugar, y no conoce dias festivos todavia — eso es dato maestro y entra cuando exista el ERP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Literal

from services.common.errors import ErrorDeValidacion

# Hora del centro de Mexico. Offset fijo a proposito: Mexico elimino el horario de verano en
# octubre de 2022, asi que -6 vale todo el año y no hace falta base de datos de husos.
#
# Que el calendario corra en hora local no es un detalle: los timestamps del registro son UTC,
# y aplicarles un horario de 9 a 18 sin convertir pondria la jornada de 3 de la mañana a
# mediodia. Un SLA mal encajado en el dia es peor que no tener SLA, porque parece que funciona.
HUSO = timezone(timedelta(hours=-6), "CST-MX")

APERTURA = time(9, 0)
CIERRE = time(18, 0)
HORAS_POR_DIA = 9
DIAS_HABILES = (0, 1, 2, 3, 4)  # lunes a viernes


def a_local(momento: datetime) -> datetime:
    """Lleva cualquier momento a la hora de oficina. Un naive se asume ya local."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=HUSO)
    return momento.astimezone(HUSO)

# §7.3: por criticidad, cuanto se espera y que pasa al vencer.
SLA = {
    "alta": {"horas_habiles": 4, "al_vencer": "escalar", "luego": "bloquear"},
    "media": {"dias_habiles": 1, "al_vencer": "escalar", "luego": "expirar"},
    "baja": {"dias_habiles": 3, "al_vencer": "expirar", "luego": "expirar"},
}

ACCIONES = ("escalar", "expirar", "bloquear")


class NuncaAutoAprueba(AssertionError):
    """Se intento resolver un vencimiento aprobando. Es la unica salida prohibida."""


def es_habil(momento: datetime) -> bool:
    local = a_local(momento)
    return local.weekday() in DIAS_HABILES and APERTURA <= local.time() < CIERRE


def _siguiente_apertura(momento: datetime) -> datetime:
    candidato = momento
    if candidato.time() >= CIERRE:
        candidato = (candidato + timedelta(days=1)).replace(
            hour=APERTURA.hour, minute=APERTURA.minute, second=0, microsecond=0
        )
    elif candidato.time() < APERTURA:
        candidato = candidato.replace(hour=APERTURA.hour, minute=APERTURA.minute, second=0, microsecond=0)
    while candidato.weekday() not in DIAS_HABILES:
        candidato = (candidato + timedelta(days=1)).replace(
            hour=APERTURA.hour, minute=APERTURA.minute, second=0, microsecond=0
        )
    return candidato


def sumar_horas_habiles(desde: datetime, horas: float) -> datetime:
    """Avanza `horas` de reloj laboral desde un momento cualquiera."""
    if horas < 0:
        raise ErrorDeValidacion("no se puede sumar un SLA negativo", campo="horas")
    original = desde.tzinfo or HUSO
    momento = _siguiente_apertura(a_local(desde))
    restante = timedelta(hours=horas)

    while restante > timedelta(0):
        fin_del_dia = momento.replace(hour=CIERRE.hour, minute=CIERRE.minute, second=0, microsecond=0)
        disponible = fin_del_dia - momento
        if restante <= disponible:
            return (momento + restante).astimezone(original)
        restante -= disponible
        momento = _siguiente_apertura(fin_del_dia)
    return momento.astimezone(original)


def sumar_dias_habiles(desde: datetime, dias: int) -> datetime:
    return sumar_horas_habiles(desde, dias * HORAS_POR_DIA)


def vencimiento(desde: datetime, criticidad: str) -> datetime:
    if criticidad not in SLA:
        raise ErrorDeValidacion(f"criticidad desconocida: {criticidad!r}", campo="criticidad")
    regla = SLA[criticidad]
    if "horas_habiles" in regla:
        return sumar_horas_habiles(desde, regla["horas_habiles"])
    return sumar_dias_habiles(desde, regla["dias_habiles"])


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
    *, trace_id: str, criticidad: str, espera_desde: datetime, ahora: datetime, escalamientos: int = 0
) -> Vencimiento | None:
    """Que hacer con un HITL que espera. `None` si todavia no vence.

    La salida nunca es "aprobar" — por eso la funcion no tiene ese caso ni puede tenerlo.
    Alta escala y deja el caso bloqueado; media escala una vez y luego expira; baja expira.
    """
    if criticidad not in SLA:
        raise ErrorDeValidacion(f"criticidad desconocida: {criticidad!r}", campo="criticidad")

    limite = vencimiento(espera_desde, criticidad)
    if ahora < limite:
        return None

    regla = SLA[criticidad]
    accion = regla["al_vencer"] if escalamientos == 0 else regla["luego"]
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
