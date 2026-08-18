"""Primitivas compartidas por los servicios deterministicos."""

from services.common.errors import (
    EntradaFaltante,
    ErrorDeServicio,
    ErrorDeIntegridad,
    ErrorDeValidacion,
)
from services.common.money import cantidad, cuota, mxn, pct
from services.common.result import Supuesto

__all__ = [
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
