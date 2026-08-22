"""svc-cfdi-validate - Validacion de CFDI y Carta Porte.

Fase 2. Sin consumo de LLM: "un LLM aqui solo anade riesgo" (§6.2).
Contrato: registry/services/svc-cfdi-validate.yaml.
"""

from services.cfdi_validate.dictamen import (
    CatalogosSAT,
    DictamenCFDI,
    XMLIlegible,
    cargar_catalogos,
    validar_cfdi,
)

SERVICE_ID = "svc-cfdi-validate"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CatalogosSAT",
    "DictamenCFDI",
    "XMLIlegible",
    "cargar_catalogos",
    "validar_cfdi",
]
