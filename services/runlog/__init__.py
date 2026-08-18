"""svc-runlog - Registro del camino y el progreso de cada caso.

Fase 1. Sin consumo de LLM. Contrato: registry/services/svc-runlog.yaml.
"""

from services.runlog.caso import (
    BLOQUEADO,
    ENTREGADO,
    ESPERANDO_HUMANO,
    ESPERANDO_VALIDACION,
    ESTADOS,
    EN_PROCESO,
    EXPIRADO,
    MAX_REINTENTOS,
    RECHAZADO_VALIDACION,
    RECIBIDO,
    Caso,
    Paso,
    ReintentosAgotados,
    TransicionInvalida,
)
from services.runlog.registro import Progreso, RunLog, entregar
from services.runlog.sla import (
    SLA,
    NuncaAutoAprueba,
    Vencimiento,
    es_habil,
    resolver_vencimiento,
    sumar_dias_habiles,
    sumar_horas_habiles,
    vencimiento,
)

SERVICE_ID = "svc-runlog"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "BLOQUEADO",
    "Caso",
    "ENTREGADO",
    "ESPERANDO_HUMANO",
    "ESPERANDO_VALIDACION",
    "ESTADOS",
    "EN_PROCESO",
    "EXPIRADO",
    "MAX_REINTENTOS",
    "NuncaAutoAprueba",
    "Paso",
    "Progreso",
    "RECHAZADO_VALIDACION",
    "RECIBIDO",
    "ReintentosAgotados",
    "RunLog",
    "SLA",
    "TransicionInvalida",
    "Vencimiento",
    "entregar",
    "es_habil",
    "resolver_vencimiento",
    "sumar_dias_habiles",
    "sumar_horas_habiles",
    "vencimiento",
]
