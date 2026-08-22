"""svc-ap - Cuentas por pagar, calendario y prioridad de pago.

Fase 3. Sin consumo de LLM. Contrato: registry/services/svc-ap.yaml.
"""

from services.ap.cuentas_por_pagar import (
    ConciliacionPagos,
    CuentaPorPagar,
    Pagos,
    PagoRealizado,
    RubricaPagos,
    Tramo,
    analizar,
    cargar_rubrica,
    conciliar,
)

SERVICE_ID = "svc-ap"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "ConciliacionPagos",
    "CuentaPorPagar",
    "Pagos",
    "PagoRealizado",
    "RubricaPagos",
    "Tramo",
    "analizar",
    "cargar_rubrica",
    "conciliar",
]
