"""svc-validation - QA transversal: reglas deterministicas por dominio.

Fase 1. Sin consumo de LLM. Contrato: registry/services/svc-validation.yaml.
"""

from services.validation.reglas import (
    CAMPOS_ENTREGABLE,
    CATALOGO,
    Dictamen,
    EntregableRechazado,
    Hallazgo,
    Regla,
    exigir,
    registrar,
    regla,
    validar,
)

SERVICE_ID = "svc-validation"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CAMPOS_ENTREGABLE",
    "CATALOGO",
    "Dictamen",
    "EntregableRechazado",
    "Hallazgo",
    "Regla",
    "exigir",
    "registrar",
    "regla",
    "validar",
]
