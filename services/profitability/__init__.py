"""svc-profitability - Margen por viaje, ruta, cliente, unidad y operador.

Fase 0. Sin consumo de LLM. Contrato: registry/services/svc-profitability.yaml.
"""

from services.profitability.margen import (
    DIMENSIONES,
    ContrasteTarifas,
    DesviacionTarifa,
    Distribucion,
    MargenAgregado,
    MargenViaje,
    agregar,
    contraste_margen_minimo,
    distribucion,
    margen_viaje,
    percentil,
)

SERVICE_ID = "svc-profitability"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "DIMENSIONES",
    "ContrasteTarifas",
    "DesviacionTarifa",
    "Distribucion",
    "MargenAgregado",
    "MargenViaje",
    "agregar",
    "contraste_margen_minimo",
    "distribucion",
    "margen_viaje",
    "percentil",
]
