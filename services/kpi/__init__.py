"""svc-kpi - Indicadores homologados por departamento, con semáforo.

Fase 3. Sin consumo de LLM. Contrato: registry/services/svc-kpi.yaml.
"""

from services.kpi.tablero import (
    CatalogoKPI,
    DefinicionKPI,
    Indicador,
    KPIDesconocido,
    Tablero,
    cargar_catalogo,
    construir_tablero,
)

SERVICE_ID = "svc-kpi"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "CatalogoKPI",
    "DefinicionKPI",
    "Indicador",
    "KPIDesconocido",
    "Tablero",
    "cargar_catalogo",
    "construir_tablero",
]
