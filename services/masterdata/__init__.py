"""svc-masterdata - Catalogo unico: clientes, unidades, operadores, rutas, tarifas.

Fase 0. Sin consumo de LLM. Contrato: registry/services/svc-masterdata.yaml.
"""

from services.masterdata.catalogo import Catalogo, ProblemaDeIntegridad
from services.masterdata.loader import cargar_catalogo, cargar_parametros, leer_csv
from services.masterdata.models import (
    Cliente,
    Operador,
    Parametros,
    Ruta,
    Tarifa,
    Unidad,
    booleano,
    fecha,
)

SERVICE_ID = "svc-masterdata"
VERSION = "v1.0.0"

__all__ = [
    "SERVICE_ID",
    "VERSION",
    "Catalogo",
    "Cliente",
    "Operador",
    "Parametros",
    "ProblemaDeIntegridad",
    "Ruta",
    "Tarifa",
    "Unidad",
    "booleano",
    "cargar_catalogo",
    "cargar_parametros",
    "fecha",
    "leer_csv",
]
