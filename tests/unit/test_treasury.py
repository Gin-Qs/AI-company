"""svc-treasury: el saldo corre día a día y los días de caja no fingen ser infinitos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.ingest.registros import MovimientoBancario
from services.treasury import construir, dias_de_caja, gasto_diario_promedio, posicion_diaria


def movimiento(fecha, monto, referencia="", cuenta="001") -> MovimientoBancario:
    return MovimientoBancario(
        fecha=fecha, concepto="mov", monto_mxn=Decimal(monto), cuenta=cuenta, referencia=referencia, origen="banco"
    )


def test_saldo_corre_dia_a_dia_sobre_los_movimientos():
    movimientos = [
        movimiento(date(2026, 6, 1), "1000.00"),
        movimiento(date(2026, 6, 2), "-300.00"),
        movimiento(date(2026, 6, 2), "-100.00"),
        movimiento(date(2026, 6, 4), "500.00"),
    ]

    diaria, saldo_final = posicion_diaria(movimientos, saldo_inicial_mxn="2000.00", corte=date(2026, 6, 4))

    assert [d.fecha for d in diaria] == [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 4)]
    assert diaria[0].saldo_mxn == Decimal("3000.00")
    assert diaria[1].egresos_mxn == Decimal("400.00")
    assert diaria[1].saldo_mxn == Decimal("2600.00")
    assert saldo_final == Decimal("3100.00")


def test_un_movimiento_despues_del_corte_no_se_cuenta():
    movimientos = [movimiento(date(2026, 6, 1), "1000.00"), movimiento(date(2026, 6, 10), "-9000.00")]

    _, saldo = posicion_diaria(movimientos, saldo_inicial_mxn="0", corte=date(2026, 6, 1))

    assert saldo == Decimal("1000.00")


def test_el_flujo_proyectado_suma_cobros_y_resta_pagos():
    resultado = construir(
        [],
        saldo_inicial_mxn="10000.00",
        corte=date(2026, 6, 1),
        flujo_esperado_cobros={"2026-W23": Decimal("5000.00"), "2026-W24": Decimal("3000.00")},
        calendario_pagos={"2026-W23": Decimal("2000.00")},
    )

    assert resultado.flujo_semanal["2026-W23"] == Decimal("13000.00")   # 10000 + 5000 - 2000
    assert resultado.flujo_semanal["2026-W24"] == Decimal("16000.00")   # 13000 + 3000


def test_dias_de_caja_compara_saldo_contra_gasto_promedio():
    movimientos = [movimiento(date(2026, 6, d), "-300.00") for d in range(1, 6)]  # 5 dias, $300/dia

    gasto = gasto_diario_promedio(movimientos, corte=date(2026, 6, 5), dias_historial=5)
    dias = dias_de_caja(Decimal("6000.00"), gasto)

    assert gasto == Decimal("300.00")
    assert dias == Decimal("20.0")


def test_un_gasto_diario_promedio_en_cero_no_revienta_el_calculo():
    """Sin egresos historicos, dias_de_caja es indeterminado, no infinito."""
    movimientos = [movimiento(date(2026, 6, 1), "1000.00")]  # sólo ingresos

    resultado = construir(movimientos, saldo_inicial_mxn="0", corte=date(2026, 6, 1))

    assert resultado.gasto_diario_promedio_mxn == Decimal("0.00")
    assert resultado.dias_de_caja is None
    assert any("no se puede calcular" in a for a in resultado.assumptions)


def test_el_saldo_inicial_declarado_queda_en_los_supuestos():
    resultado = construir([], saldo_inicial_mxn="1234.50", corte=date(2026, 6, 1))

    assert resultado.saldo_actual_mxn == Decimal("1234.50")
    assert any("1234.50" in a for a in resultado.assumptions)
