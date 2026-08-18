"""Bitacora de la oficina: append-only, un evento por linea.

Precursor de `svc-runlog` (fase 1). Mientras ese servicio no existe, esto cumple su regla
central, que es la R7 de la arquitectura: **si no esta en la bitacora, no ocurrio.**

Formato JSONL para que crezca sin reescribirse y para que un `tail` sirva de monitor.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "office" / "bitacora.jsonl"

EVENTOS = (
    "convocatoria",   # se le encarga algo a un agente
    "inicio",         # el agente empieza a trabajar
    "entrega",        # el agente entrega
    "bloqueo",        # el caso se detiene: falta contexto o falta una aprobacion humana
    "desbloqueo",
    "cierre",
    "nota",           # el agente anota en su memoria
    "evaluacion",     # D5-03 revisa calidad
)


@dataclass(frozen=True)
class Entrada:
    ts: str
    trace_id: str
    evento: str
    agente: str
    encargo: str
    detalle: str
    autor: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def leer(limite: int | None = None) -> list[Entrada]:
    if not ARCHIVO.is_file():
        return []
    entradas: list[Entrada] = []
    for linea in ARCHIVO.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        datos = json.loads(linea)
        entradas.append(Entrada(**datos))
    return entradas[-limite:] if limite else entradas


def nuevo_trace(prefijo: str = "TR") -> str:
    """Un trace por convocatoria, legible y ordenable: TR-20260818-003."""
    hoy = _ahora().strftime("%Y%m%d")
    del_dia = {e.trace_id for e in leer() if e.trace_id.startswith(f"{prefijo}-{hoy}")}
    return f"{prefijo}-{hoy}-{len(del_dia) + 1:03d}"


def registrar(
    *,
    evento: str,
    agente: str,
    encargo: str = "-",
    detalle: str = "",
    autor: str = "sistema",
    trace_id: str | None = None,
) -> Entrada:
    if evento not in EVENTOS:
        raise ValueError(f"evento desconocido: {evento!r}; validos: {', '.join(EVENTOS)}")

    entrada = Entrada(
        ts=_ahora().isoformat(timespec="seconds"),
        trace_id=trace_id or nuevo_trace(),
        evento=evento,
        agente=agente,
        encargo=encargo,
        detalle=" ".join(detalle.split()),
        autor=autor,
    )
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVO.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(entrada.as_dict(), ensure_ascii=False) + "\n")
    return entrada


def trace_de(encargo_id: str) -> list[Entrada]:
    """Todo lo que le paso a un encargo, en orden. Es la respuesta a '¿en que va esto?'."""
    return [e for e in leer() if e.encargo == encargo_id]
