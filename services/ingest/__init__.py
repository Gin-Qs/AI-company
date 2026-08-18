"""svc-ingest - Normalizacion de bancos, tickets de diesel, GPS y CSV del ERP.

Fase 0. Sin consumo de LLM. Contrato: registry/services/svc-ingest.yaml.
"""

from services.ingest.normalizador import (
    Rechazo,
    ResultadoIngesta,
    normalizar_banco,
    normalizar_diesel,
    normalizar_gps,
    normalizar_viajes,
    precio_diesel_promedio,
)
from services.ingest.registros import CargaDiesel, MovimientoBancario, RecorridoGPS, Viaje

SERVICE_ID = "svc-ingest"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CargaDiesel",
    "MovimientoBancario",
    "Rechazo",
    "RecorridoGPS",
    "ResultadoIngesta",
    "Viaje",
    "normalizar_banco",
    "normalizar_diesel",
    "normalizar_gps",
    "normalizar_viajes",
    "precio_diesel_promedio",
]
