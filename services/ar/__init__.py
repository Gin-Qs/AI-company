"""svc-ar - Cartera, aging y prioridad de cobranza.

Fase 2. Sin consumo de LLM. Contrato: registry/services/svc-ar.yaml.
"""

from services.ar.cartera import (
    Cartera,
    Conciliacion,
    Factura,
    Pago,
    Rubrica,
    Saldo,
    Tramo,
    analizar,
    cargar_rubrica,
    conciliar,
)
from services.ar.desde_operacion import CarteraDeOperacion, construir as cartera_desde_operacion

SERVICE_ID = "svc-ar"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Cartera",
    "CarteraDeOperacion",
    "cartera_desde_operacion",
    "Conciliacion",
    "Factura",
    "Pago",
    "Rubrica",
    "Saldo",
    "Tramo",
    "analizar",
    "cargar_rubrica",
    "conciliar",
]
