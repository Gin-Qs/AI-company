"""Tesorería a partir de lo que ya normalizó la Fase 0 y calculó la Fase 2.

`svc-ingest` deja el banco en forma canónica desde la Fase 0; `svc-ar` ya calcula el flujo
esperado de cobranza. Con eso se arma la posición de caja sin volver a capturar nada — salvo
el saldo inicial, que nadie puede deducir de un CSV de movimientos.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from services.ap.cuentas_por_pagar import Pagos
from services.ar.cartera import Cartera
from services.ingest.normalizador import normalizar_banco
from services.masterdata.loader import leer_csv
from services.treasury.posicion import Tesoreria, construir


def construir_desde_datos(
    datos: str | Path,
    *,
    saldo_inicial_mxn: object,
    corte: date,
    cartera: Cartera | None = None,
    pagos: Pagos | None = None,
    dias_historial: int = 30,
) -> Tesoreria:
    """Arma la tesorería desde `data/<lo que sea>/operacion/banco.csv`.

    `cartera` y `pagos` son opcionales a propósito: sin ellos, `flujo_semanal` sólo refleja
    movimientos ya ocurridos, que sigue siendo una posición de caja válida — sólo que sin
    proyección hacia adelante.
    """
    raiz = Path(datos)
    banco = normalizar_banco(leer_csv(raiz / "operacion" / "banco.csv"))

    return construir(
        banco.registros,
        saldo_inicial_mxn=saldo_inicial_mxn,
        corte=corte,
        flujo_esperado_cobros=cartera.flujo_esperado if cartera else None,
        calendario_pagos=pagos.calendario if pagos else None,
        dias_historial=dias_historial,
    )
