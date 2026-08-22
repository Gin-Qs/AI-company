"""svc-doc-checklist - Completitud documental del viaje antes de facturar.

Fase 2. Sin consumo de LLM. Contrato: registry/services/svc-doc-checklist.yaml.
"""

from services.doc_checklist.expediente import (
    FALTA,
    NO_APLICA,
    VENCIDO,
    CatalogoDocumental,
    Documento,
    Expediente,
    ExpedienteIncompleto,
    Faltante,
    Requisito,
    TipoDeServicioDesconocido,
    cargar_catalogo_documental,
    concepto_respaldado,
    exigir_completo,
    revisar,
)

SERVICE_ID = "svc-doc-checklist"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "FALTA",
    "NO_APLICA",
    "VENCIDO",
    "CatalogoDocumental",
    "Documento",
    "Expediente",
    "ExpedienteIncompleto",
    "Faltante",
    "Requisito",
    "TipoDeServicioDesconocido",
    "cargar_catalogo_documental",
    "concepto_respaldado",
    "exigir_completo",
    "revisar",
]
