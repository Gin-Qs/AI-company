"""svc-alerts - Motor de reglas sobre umbrales y selección del brief.

Fase 3. Sin consumo de LLM. Contrato: registry/services/svc-alerts.yaml.
"""

from services.alerts.motor import (
    Alerta,
    ReglasAlertas,
    Seleccion,
    cargar_reglas,
    evaluar,
)

SERVICE_ID = "svc-alerts"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Alerta",
    "ReglasAlertas",
    "Seleccion",
    "cargar_reglas",
    "evaluar",
]
