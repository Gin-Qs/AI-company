"""svc-budget - Presupuesto de tokens por agente, alerta al 80%.

Fase 1. Sin consumo de LLM. Contrato: registry/services/svc-budget.yaml.
"""

from services.budget.control import (
    Autorizacion,
    EstadoPresupuesto,
    Politica,
    PresupuestoExcedido,
    autorizar,
    cargar_politica,
    evaluar,
    exigir,
    panorama,
)

SERVICE_ID = "svc-budget"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Autorizacion",
    "EstadoPresupuesto",
    "Politica",
    "PresupuestoExcedido",
    "autorizar",
    "cargar_politica",
    "evaluar",
    "exigir",
    "panorama",
]
