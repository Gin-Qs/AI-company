"""svc-costing - Costo por km y por viaje.

Fase 0. Sin consumo de LLM. Contrato: registry/services/svc-costing.yaml.
Fuente unica del numero: ningun agente vuelve a calcular un costo por km.
"""

from services.costing.motor import (
    CONCEPTOS_VARIABLES,
    EntradaCosteo,
    ResultadoCosteo,
    costear,
    costear_viaje,
)

SERVICE_ID = "svc-costing"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CONCEPTOS_VARIABLES",
    "EntradaCosteo",
    "ResultadoCosteo",
    "costear",
    "costear_viaje",
]
