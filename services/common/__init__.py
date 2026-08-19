"""Primitivas compartidas por los servicios deterministicos."""

from services.common.errors import (
    EntradaFaltante,
    ErrorDeServicio,
    ErrorDeIntegridad,
    ErrorDeValidacion,
)
from services.common.money import cantidad, cuota, mxn, pct
from services.common.result import Autorizacion, Supuesto

__all__ = [
    "Autorizacion",
    "EntradaFaltante",
    "ErrorDeServicio",
    "ErrorDeIntegridad",
    "ErrorDeValidacion",
    "cantidad",
    "cuota",
    "mxn",
    "pct",
    "Supuesto",
]
