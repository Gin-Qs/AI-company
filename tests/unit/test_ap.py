"""svc-ap: el espejo de svc-ar del lado de lo que se paga."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.ap import CuentaPorPagar, PagoRealizado, analizar, cargar_rubrica, conciliar

CORTE = date(2026, 6, 1)


@pytest.fixture
def rubrica():
    return cargar_rubrica()


def cuenta(cuenta_id, proveedor_id, emision, dias_credito, total) -> CuentaPorPagar:
    return CuentaPorPagar(
        cuenta_id=cuenta_id,
        proveedor_id=proveedor_id,
        fecha_emision=emision,
        dias_credito=dias_credito,
        total_mxn=Decimal(total),
    )


def test_calendario_ordena_por_vencimiento(rubrica):
    cuentas = [
        cuenta("CP-1", "PROV-1", date(2026, 6, 5), 15, "3000.00"),    # vence 20-jun: por venir
        cuenta("CP-2", "PROV-2", date(2026, 6, 20), 30, "1000.00"),   # vence 20-jul: por venir
    ]

    pagos = analizar(conciliar(cuentas, []), corte=CORTE, rubrica=rubrica)

    assert sum(pagos.calendario.values()) == Decimal("4000.00")
    assert pagos.saldo_total_mxn == Decimal("4000.00")
    assert pagos.saldo_vencido_mxn == Decimal("0.00")


def test_una_cuenta_vencida_entra_al_tramo_correcto(rubrica):
    cuentas = [cuenta("CP-1", "PROV-1", date(2026, 1, 10), 30, "5000.00")]   # vence 9-feb: 112 dias

    pagos = analizar(conciliar(cuentas, []), corte=CORTE, rubrica=rubrica)

    assert pagos.vencido["60+"] == Decimal("5000.00")
    assert pagos.saldo_vencido_mxn == Decimal("5000.00")


def test_un_pago_parcial_reduce_el_saldo_no_la_antiguedad(rubrica):
    cuentas = [cuenta("CP-1", "PROV-1", date(2026, 1, 10), 30, "5000.00")]
    pagos_hechos = [PagoRealizado(fecha=date(2026, 5, 31), monto_mxn=Decimal("2000.00"), cuenta_id="CP-1")]

    pagos = analizar(conciliar(cuentas, pagos_hechos), corte=CORTE, rubrica=rubrica)

    assert pagos.vencido["60+"] == Decimal("3000.00")
    assert pagos.prioridad[0]["dias_vencido"] == 112


def test_prioridad_de_pago_sale_de_regla_no_de_criterio(rubrica):
    """§9.1: todo ranking con consecuencia lleva rúbrica versionada, y la versión viaja."""
    cuentas = [
        cuenta("CP-CHICA-VIEJA", "PROV-1", date(2026, 1, 10), 30, "1000.00"),   # 112 dias
        cuenta("CP-GRANDE-NUEVA", "PROV-2", date(2026, 4, 20), 30, "40000.00"),  # 12 dias
    ]

    pagos = analizar(conciliar(cuentas, []), corte=CORTE, rubrica=rubrica)
    orden = [fila["cuenta_id"] for fila in pagos.prioridad]

    assert orden == ["CP-GRANDE-NUEVA", "CP-CHICA-VIEJA"]
    assert all(fila["rubrica_version"] == rubrica.version for fila in pagos.prioridad)
    assert pagos.rubrica_calibrada is False


def test_un_proveedor_critico_suma_puntos_extra(rubrica):
    from dataclasses import replace

    rubrica_con_critico = replace(rubrica, proveedores_criticos=("PROV-DIESEL",))
    cuentas = [
        cuenta("CP-1", "PROV-DIESEL", date(2026, 5, 1), 15, "1000.00"),   # vence 16-may: 16 dias
        cuenta("CP-2", "PROV-2", date(2026, 5, 1), 15, "1000.00"),
    ]

    pagos = analizar(conciliar(cuentas, []), corte=CORTE, rubrica=rubrica_con_critico)

    assert pagos.prioridad[0]["cuenta_id"] == "CP-1"
    assert pagos.prioridad[0]["proveedor_critico"] is True


def test_un_pago_sin_referencia_no_se_reparte(rubrica):
    cuentas = [cuenta("CP-1", "PROV-1", date(2026, 4, 1), 30, "10000.00")]
    pagos_hechos = [PagoRealizado(fecha=date(2026, 5, 2), monto_mxn=Decimal("4000.00"), referencia="SPEI SALIENTE")]

    conciliacion = conciliar(cuentas, pagos_hechos)
    pagos = analizar(conciliacion, corte=CORTE, rubrica=rubrica)

    assert len(conciliacion.sin_identificar) == 1
    assert pagos.sin_identificar_mxn == Decimal("4000.00")
    assert pagos.saldo_total_mxn == Decimal("10000.00")


def test_una_cuenta_liquidada_sale_del_calendario(rubrica):
    cuentas = [cuenta("CP-1", "PROV-1", date(2026, 6, 5), 30, "5000.00")]
    pagos_hechos = [PagoRealizado(fecha=date(2026, 6, 10), monto_mxn=Decimal("5000.00"), cuenta_id="CP-1")]

    pagos = analizar(conciliar(cuentas, pagos_hechos), corte=CORTE, rubrica=rubrica)

    assert pagos.saldo_total_mxn == Decimal("0.00")
    assert pagos.calendario == {}
    assert pagos.prioridad == []
