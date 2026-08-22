"""Encargos: la unidad de trabajo de la oficina.

Un encargo es lo que la §5-bis.3 exige para convocar a un consultor: **un encargo escrito** —
que modulo, que problema, que restriccion. Aqui es un archivo YAML por encargo, con su estado
y su historia en la bitacora.

Estados y lo que significan en el plano de la oficina:

    pendiente   el escritorio esta ocupado pero el agente no ha empezado
    en_curso    el agente esta trabajando (se le ve teclear)
    bloqueado   falta contexto o falta una aprobacion humana (levanta la mano)
    hecho       entregado
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from office import bitacora

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO = RAIZ / "office" / "encargos"

ESTADOS = ("pendiente", "en_curso", "bloqueado", "hecho")
TRANSICIONES = {
    "pendiente": ("en_curso", "bloqueado"),
    "en_curso": ("bloqueado", "hecho"),
    "bloqueado": ("en_curso",),
    "hecho": (),
}


class TransicionInvalida(ValueError):
    """Se intento un cambio de estado que el flujo no permite."""


@dataclass
class Encargo:
    id: str
    titulo: str
    agente: str
    convocado_por: str
    estado: str = "pendiente"
    descripcion: str = ""
    entregable_esperado: str = ""
    depende_de: list[str] = field(default_factory=list)
    hitl: bool = False
    creado: str = ""
    actualizado: str = ""
    trace_id: str = ""

    @property
    def abierto(self) -> bool:
        return self.estado != "hecho"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "agente": self.agente,
            "convocado_por": self.convocado_por,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "entregable_esperado": self.entregable_esperado,
            "depende_de": list(self.depende_de),
            "hitl": self.hitl,
            "creado": self.creado,
            "actualizado": self.actualizado,
            "trace_id": self.trace_id,
        }


def ruta(encargo_id: str) -> Path:
    return DIRECTORIO / f"{encargo_id}.yaml"


def guardar(encargo: Encargo) -> Path:
    destino = ruta(encargo.id)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        yaml.safe_dump(encargo.as_dict(), allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    return destino


def cargar_todos() -> dict[str, Encargo]:
    if not DIRECTORIO.is_dir():
        return {}
    encargos: dict[str, Encargo] = {}
    for archivo in sorted(DIRECTORIO.glob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
        encargo = Encargo(**datos)
        encargos[encargo.id] = encargo
    return encargos


def cargar(encargo_id: str) -> Encargo:
    encargos = cargar_todos()
    if encargo_id not in encargos:
        raise KeyError(f"encargo inexistente: {encargo_id}")
    return encargos[encargo_id]


def siguiente_id() -> str:
    existentes = [int(e[2:]) for e in cargar_todos() if e.startswith("E-") and e[2:].isdigit()]
    return f"E-{max(existentes, default=0) + 1:03d}"


def crear(
    *,
    titulo: str,
    agente: str,
    convocado_por: str,
    descripcion: str = "",
    entregable_esperado: str = "",
    depende_de: list[str] | None = None,
    hitl: bool = False,
    encargo_id: str | None = None,
    cuando: date | None = None,
) -> Encargo:
    hoy = (cuando or date.today()).isoformat()
    encargo = Encargo(
        id=encargo_id or siguiente_id(),
        titulo=titulo.strip(),
        agente=agente,
        convocado_por=convocado_por,
        descripcion=" ".join(descripcion.split()),
        entregable_esperado=entregable_esperado.strip(),
        depende_de=list(depende_de or []),
        hitl=hitl,
        creado=hoy,
        actualizado=hoy,
        trace_id=bitacora.nuevo_trace(),
    )
    guardar(encargo)
    bitacora.registrar(
        evento="convocatoria",
        agente=agente,
        encargo=encargo.id,
        detalle=encargo.titulo,
        autor=convocado_por,
        trace_id=encargo.trace_id,
        hitl=encargo.hitl,
        # Un encargo que necesita firma humana entra como caso critico: su SLA en la bandeja
        # de HITL se mide en horas habiles, no en dias (§7.3).
        criticidad="alta" if encargo.hitl else "media",
    )
    return encargo


EVENTO_POR_ESTADO = {
    "en_curso": "inicio",
    "bloqueado": "bloqueo",
    "hecho": "cierre",
}


def avanzar(encargo_id: str, nuevo_estado: str, *, autor: str, nota: str = "") -> Encargo:
    """Cambia el estado y lo registra. Un cambio de estado sin rastro no vale (R7)."""
    if nuevo_estado not in ESTADOS:
        raise ValueError(f"estado desconocido: {nuevo_estado!r}")

    encargo = cargar(encargo_id)
    if nuevo_estado not in TRANSICIONES[encargo.estado]:
        raise TransicionInvalida(
            f"{encargo_id} esta {encargo.estado} y no puede pasar a {nuevo_estado}; "
            f"permitido: {', '.join(TRANSICIONES[encargo.estado]) or 'nada, ya cerro'}"
        )

    anterior = encargo.estado
    encargo.estado = nuevo_estado
    encargo.actualizado = date.today().isoformat()
    guardar(encargo)

    evento = EVENTO_POR_ESTADO[nuevo_estado]
    if anterior == "bloqueado" and nuevo_estado == "en_curso":
        evento = "desbloqueo"
    bitacora.registrar(
        evento=evento,
        agente=encargo.agente,
        encargo=encargo.id,
        detalle=nota or f"{anterior} -> {nuevo_estado}",
        autor=autor,
        trace_id=encargo.trace_id,
        hitl=encargo.hitl,
    )
    return encargo


def por_agente() -> dict[str, list[Encargo]]:
    agrupados: dict[str, list[Encargo]] = {}
    for encargo in cargar_todos().values():
        agrupados.setdefault(encargo.agente, []).append(encargo)
    orden = {estado: indice for indice, estado in enumerate(("bloqueado", "en_curso", "pendiente", "hecho"))}
    for lista in agrupados.values():
        lista.sort(key=lambda e: (orden[e.estado], e.id))
    return agrupados
