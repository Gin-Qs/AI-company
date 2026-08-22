"""svc-notify - Avisos por plantilla fija, sin LLM.

Fase 2. Contrato: registry/services/svc-notify.yaml.
"""

from services.notify.plantillas import (
    CanalNoDisponible,
    CatalogoPlantillas,
    DestinatarioDesconocido,
    Envio,
    Mensaje,
    Plantilla,
    PlantillaDesconocida,
    Variable,
    VariableInvalida,
    cargar_plantillas,
    enviar,
    render,
)

SERVICE_ID = "svc-notify"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CanalNoDisponible",
    "CatalogoPlantillas",
    "DestinatarioDesconocido",
    "Envio",
    "Mensaje",
    "Plantilla",
    "PlantillaDesconocida",
    "Variable",
    "VariableInvalida",
    "cargar_plantillas",
    "enviar",
    "render",
]
