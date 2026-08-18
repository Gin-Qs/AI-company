"""Aritmetica de dinero y de cuotas.

Todo importe es `Decimal`. Nada de `float`: un margen de 0.1% sobre una
tarifa se pierde en el redondeo binario y despues nadie sabe por que el
reporte no cuadra con la factura.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from services.common.errors import ErrorDeValidacion

CENTAVO = Decimal("0.01")
CUATRO_DECIMALES = Decimal("0.0001")


def cantidad(valor: object, *, campo: str = "valor") -> Decimal:
    """Convierte a Decimal aceptando texto contable: '$ 1,234.50', '(120)', '1 234,50'."""
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        # Pasa por str para no arrastrar el ruido binario del float de origen.
        return Decimal(str(valor))
    if valor is None:
        raise ErrorDeValidacion("valor nulo", campo=campo)

    texto = str(valor).strip()
    if not texto:
        raise ErrorDeValidacion("valor vacio", campo=campo)

    negativo = texto.startswith("(") and texto.endswith(")")
    if negativo:
        texto = texto[1:-1]
    texto = texto.replace("$", "").replace(" ", "").replace("\u00a0", "")
    if "," in texto and "." in texto:
        # La ultima aparicion manda: '1.234,50' es europeo, '1,234.50' es mexicano.
        texto = texto.replace(",", "") if texto.rfind(".") > texto.rfind(",") else texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        entero, _, resto = texto.rpartition(",")
        texto = f"{entero}.{resto}" if len(resto) in (1, 2) and entero else texto.replace(",", "")

    try:
        numero = Decimal(texto)
    except InvalidOperation as exc:
        raise ErrorDeValidacion(f"no es un numero: {valor!r}", campo=campo) from exc
    return -numero if negativo else numero


def mxn(valor: object, *, campo: str = "importe") -> Decimal:
    """Importe en pesos, redondeado a centavo (mitad hacia arriba)."""
    return cantidad(valor, campo=campo).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def cuota(valor: object, *, campo: str = "cuota") -> Decimal:
    """Valor unitario ($/km, l/km, %). Cuatro decimales: a 500 km, el cuarto decimal ya son centavos."""
    return cantidad(valor, campo=campo).quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)


def pct(parte: Decimal, total: Decimal, *, campo: str = "porcentaje") -> Decimal:
    """Porcentaje parte/total con dos decimales. Total cero es un error, no un 0%."""
    if total == 0:
        raise ErrorDeValidacion("porcentaje sobre total cero", campo=campo)
    return ((parte / total) * Decimal(100)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def positivo(valor: Decimal, *, campo: str) -> Decimal:
    if valor <= 0:
        raise ErrorDeValidacion(f"debe ser mayor que cero, se recibio {valor}", campo=campo)
    return valor


def no_negativo(valor: Decimal, *, campo: str) -> Decimal:
    if valor < 0:
        raise ErrorDeValidacion(f"no puede ser negativo, se recibio {valor}", campo=campo)
    return valor
