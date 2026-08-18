"""svc-pricing - Tarifa = svc-costing + margen objetivo + politica de descuento.

Fase 1. Sin consumo de LLM. Contrato: registry/services/svc-pricing.yaml.
"""

from services.pricing.tarifador import (
    AGENTE,
    DIRECCION,
    HUMANO,
    Autorizacion,
    Cotizacion,
    CotizacionBloqueada,
    EntradaCotizacion,
    PoliticaCotizacion,
    SinTarifaVigente,
    cargar_politica,
    cotizar,
    dictaminar,
    precio_para_margen,
)

SERVICE_ID = "svc-pricing"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "AGENTE",
    "Autorizacion",
    "Cotizacion",
    "CotizacionBloqueada",
    "DIRECCION",
    "EntradaCotizacion",
    "HUMANO",
    "PoliticaCotizacion",
    "SinTarifaVigente",
    "cargar_politica",
    "cotizar",
    "dictaminar",
    "precio_para_margen",
]
