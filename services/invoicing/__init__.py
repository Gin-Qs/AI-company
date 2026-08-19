"""svc-invoicing - Emision y timbrado del comprobante.

Fase 2. Sin consumo de LLM. Contrato: registry/services/svc-invoicing.yaml.
"""

from services.invoicing.comprobante import (
    Borrador,
    Concepto,
    ConceptoSinRespaldo,
    EntradaFactura,
    LibroDeFolios,
    PoliticaFacturacion,
    Timbrado,
    TimbradoRequiereHumano,
    ViajeYaFacturado,
    armar_borrador,
    cargar_politica,
    conceptos_de_viaje,
    es_persona_moral,
    timbrar,
)

SERVICE_ID = "svc-invoicing"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Borrador",
    "Concepto",
    "ConceptoSinRespaldo",
    "EntradaFactura",
    "LibroDeFolios",
    "PoliticaFacturacion",
    "Timbrado",
    "TimbradoRequiereHumano",
    "ViajeYaFacturado",
    "armar_borrador",
    "cargar_politica",
    "conceptos_de_viaje",
    "es_persona_moral",
    "timbrar",
]
