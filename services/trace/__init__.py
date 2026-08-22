"""svc-trace - Reconciliacion cifra <-> consulta de origen.

Fase 1. Sin consumo de LLM. Contrato: registry/services/svc-trace.yaml.
"""

from services.trace.libro import (
    Cifra,
    Discrepancia,
    EntregableNoCuadra,
    Libro,
    Reconciliacion,
    exigir_reconciliacion,
    numeros_en_texto,
    reconciliar,
)

SERVICE_ID = "svc-trace"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Cifra",
    "Discrepancia",
    "EntregableNoCuadra",
    "Libro",
    "Reconciliacion",
    "exigir_reconciliacion",
    "numeros_en_texto",
    "reconciliar",
]
