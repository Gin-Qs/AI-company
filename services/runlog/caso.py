"""Modelo de svc-runlog: el paso y el caso (arquitectura v3 §8.1 y §8.2).

Dos objetos y una maquina de estados. El paso responde "que se hizo"; el caso responde
"en que va". Los dos se guardan append-only: un registro que se puede editar no es registro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from services.common.errors import ErrorDeValidacion
from services.common.money import mxn

# --- estados del caso (§8.2) ---------------------------------------------

RECIBIDO = "recibido"
EN_PROCESO = "en_proceso"
ESPERANDO_VALIDACION = "esperando_validacion"
RECHAZADO_VALIDACION = "rechazado_validacion"
ESPERANDO_HUMANO = "esperando_humano"
ENTREGADO = "entregado"
BLOQUEADO = "bloqueado"
EXPIRADO = "expirado"

ESTADOS = (
    RECIBIDO,
    EN_PROCESO,
    ESPERANDO_VALIDACION,
    RECHAZADO_VALIDACION,
    ESPERANDO_HUMANO,
    ENTREGADO,
    BLOQUEADO,
    EXPIRADO,
)

TERMINALES = (ENTREGADO, EXPIRADO)

TRANSICIONES: dict[str, tuple[str, ...]] = {
    RECIBIDO: (EN_PROCESO, BLOQUEADO),
    EN_PROCESO: (ESPERANDO_VALIDACION, ESPERANDO_HUMANO, BLOQUEADO),
    # Un caso sin gate puede entregarse en cuanto valida; uno con gate pasa por el humano.
    ESPERANDO_VALIDACION: (ESPERANDO_HUMANO, RECHAZADO_VALIDACION, ENTREGADO, BLOQUEADO),
    RECHAZADO_VALIDACION: (EN_PROCESO, BLOQUEADO),
    ESPERANDO_HUMANO: (ENTREGADO, EXPIRADO, BLOQUEADO),
    BLOQUEADO: (EN_PROCESO, EXPIRADO),
    ENTREGADO: (),
    EXPIRADO: (),
}

MAX_REINTENTOS = 2  # §12.3: el flujo de correccion permite dos, no mas

TIPOS_PASO = (
    "ruteo",
    "llamada_llm",
    "llamada_servicio",
    "validacion",
    "gate",
    "accion",
    "entrega",
)

RESULTADOS = ("ok", "fallo", "reintento", "bloqueado")

CRITICIDADES = ("alta", "media", "baja")


class TransicionInvalida(ErrorDeValidacion):
    codigo = "RUNLOG-TRANSICION"


class ReintentosAgotados(ErrorDeValidacion):
    codigo = "RUNLOG-REINTENTOS"


def ahora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Paso:
    """Un paso del arbol del caso. Los campos son los de la tabla de §8.1."""

    trace_id: str
    span_id: str
    actor: str
    tipo: str
    ts: str
    resultado: str = "ok"
    parent_span_id: str | None = None
    decision_ruteo: str = ""
    entradas: dict[str, str] = field(default_factory=dict)
    salidas: dict[str, str] = field(default_factory=dict)
    versiones: dict[str, str] = field(default_factory=dict)
    tokens: int = 0
    costo_mxn: Decimal = Decimal("0.00")
    latencia_ms: int = 0
    gate: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_PASO:
            raise ErrorDeValidacion(f"tipo de paso desconocido: {self.tipo!r}", campo="tipo")
        if self.resultado not in RESULTADOS:
            raise ErrorDeValidacion(f"resultado desconocido: {self.resultado!r}", campo="resultado")
        if self.tokens < 0 or self.latencia_ms < 0:
            raise ErrorDeValidacion("tokens y latencia no pueden ser negativos", campo="tokens")

    def as_dict(self) -> dict[str, object]:
        return {
            "evento": "paso",
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "actor": self.actor,
            "tipo": self.tipo,
            "ts": self.ts,
            "resultado": self.resultado,
            "decision_ruteo": self.decision_ruteo,
            "entradas": self.entradas,
            "salidas": self.salidas,
            "versiones": self.versiones,
            "tokens": self.tokens,
            "costo_mxn": str(self.costo_mxn),
            "latencia_ms": self.latencia_ms,
            "gate": self.gate,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Paso":
        return cls(
            trace_id=datos["trace_id"],
            span_id=datos["span_id"],
            parent_span_id=datos.get("parent_span_id"),
            actor=datos["actor"],
            tipo=datos["tipo"],
            ts=datos["ts"],
            resultado=datos.get("resultado", "ok"),
            decision_ruteo=datos.get("decision_ruteo", ""),
            entradas=datos.get("entradas") or {},
            salidas=datos.get("salidas") or {},
            versiones=datos.get("versiones") or {},
            tokens=int(datos.get("tokens") or 0),
            costo_mxn=mxn(datos.get("costo_mxn") or 0),
            latencia_ms=int(datos.get("latencia_ms") or 0),
            gate=datos.get("gate") or {},
        )


@dataclass(frozen=True)
class Transicion:
    trace_id: str
    de: str
    a: str
    ts: str
    actor: str
    motivo: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "evento": "transicion",
            "trace_id": self.trace_id,
            "de": self.de,
            "a": self.a,
            "ts": self.ts,
            "actor": self.actor,
            "motivo": self.motivo,
        }


@dataclass
class Caso:
    """Estado consultable de un caso. Se reconstruye plegando el registro, no se guarda aparte."""

    trace_id: str
    tipo: str                       # cotizacion, cierre_de_viaje, brief...
    referencia: str                 # el objeto del mundo real: T-1001, CL-01...
    criticidad: Literal["alta", "media", "baja"]
    estado: str = RECIBIDO
    abierto_en: str = ""
    actualizado_en: str = ""
    responsable: str = ""
    reintentos: int = 0
    escalamientos: int = 0
    pasos: int = 0
    tokens: int = 0
    costo_mxn: Decimal = Decimal("0.00")

    @property
    def cerrado(self) -> bool:
        return self.estado in TERMINALES

    @property
    def espera_humano(self) -> bool:
        return self.estado == ESPERANDO_HUMANO

    def puede_pasar_a(self, destino: str) -> bool:
        return destino in TRANSICIONES[self.estado]

    def exigir_transicion(self, destino: str) -> None:
        if destino not in ESTADOS:
            raise ErrorDeValidacion(f"estado desconocido: {destino!r}", campo="estado")
        if not self.puede_pasar_a(destino):
            permitidos = ", ".join(TRANSICIONES[self.estado]) or "nada, el caso ya cerro"
            raise TransicionInvalida(
                f"{self.trace_id} esta en {self.estado} y no puede pasar a {destino}; permitido: {permitidos}",
                campo="estado",
                trace_id=self.trace_id,
            )
        # El limite de reintentos no es un consejo: al tercer rechazo el caso se bloquea y
        # lo mira una persona. Sin esto, un agente que falla siempre reintenta para siempre.
        if destino == EN_PROCESO and self.estado == RECHAZADO_VALIDACION and self.reintentos >= MAX_REINTENTOS:
            raise ReintentosAgotados(
                f"{self.trace_id} agoto los {MAX_REINTENTOS} reintentos permitidos: "
                f"el caso se bloquea y pasa a revision humana",
                campo="reintentos",
                trace_id=self.trace_id,
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "tipo": self.tipo,
            "referencia": self.referencia,
            "criticidad": self.criticidad,
            "estado": self.estado,
            "abierto_en": self.abierto_en,
            "actualizado_en": self.actualizado_en,
            "responsable": self.responsable,
            "reintentos": self.reintentos,
            "escalamientos": self.escalamientos,
            "pasos": self.pasos,
            "tokens": self.tokens,
            "costo_mxn": str(self.costo_mxn),
        }
