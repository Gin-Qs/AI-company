"""svc-treasury - Posición de caja, flujo proyectado y días de caja.

Fase 3. Sin consumo de LLM. Contrato: registry/services/svc-treasury.yaml.
"""

from services.treasury.desde_operacion import construir_desde_datos
from services.treasury.posicion import (
    MovimientoDiario,
    Tesoreria,
    construir,
    dias_de_caja,
    flujo_proyectado,
    gasto_diario_promedio,
    posicion_diaria,
)

SERVICE_ID = "svc-treasury"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "MovimientoDiario",
    "Tesoreria",
    "construir",
    "construir_desde_datos",
    "dias_de_caja",
    "flujo_proyectado",
    "gasto_diario_promedio",
    "posicion_diaria",
]
