"""svc-ar: aging que no rejuvenece, prioridad con rúbrica y flujo que no cuenta dos veces."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.ar import Factura, Pago, analizar, cargar_rubrica, conciliar
from services.masterdata import cargar_catalogo

CORTE = date(2026, 6, 1)


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


@pytest.fixture
def rubrica():
    return cargar_rubrica()


def factura(factura_id, cliente_id, emision, total) -> Factura:
    return Factura(
        factura_id=factura_id,
        cliente_id=cliente_id,
        fecha_emision=emision,
        total_mxn=Decimal(total),
    )


def test_aging_reparte_por_antiguedad(catalogo, rubrica):
    """CL-01 tiene 30 días de crédito; CL-02, 45. El bucket sale del vencimiento, no de la emisión."""
    facturas = [
        factura("F-1", "CL-01", date(2026, 5, 20), "10000.00"),   # vence 19-jun: corriente
        factura("F-2", "CL-01", date(2026, 4, 15), "20000.00"),   # vence 15-may: 17 días
        factura("F-3", "CL-01", date(2026, 1, 10), "30000.00"),   # vence 9-feb: 112 días
    ]

    cartera = analizar(conciliar(facturas, [], catalogo), corte=CORTE, rubrica=rubrica)

    assert cartera.aging["corriente"] == Decimal("10000.00")
    assert cartera.aging["1-30"] == Decimal("20000.00")
    assert cartera.aging["90+"] == Decimal("30000.00")
    assert cartera.saldo_total_mxn == Decimal("60000.00")
    assert cartera.saldo_vencido_mxn == Decimal("50000.00")


def test_pago_parcial_reduce_el_saldo_no_la_antiguedad(catalogo, rubrica):
    """Una factura de hace cien días con abono de ayer sigue siendo de hace cien días."""
    facturas = [factura("F-1", "CL-01", date(2026, 1, 10), "30000.00")]
    pagos = [Pago(fecha=date(2026, 5, 31), monto_mxn=Decimal("10000.00"), factura_id="F-1")]

    cartera = analizar(conciliar(facturas, pagos, catalogo), corte=CORTE, rubrica=rubrica)

    assert cartera.aging["90+"] == Decimal("20000.00")
    assert cartera.prioridad[0]["dias_vencido"] == 112


def test_un_pago_sin_referencia_no_se_reparte(catalogo, rubrica):
    """Repartirlo entre las facturas más viejas es lo que hace que la cartera nunca cuadre."""
    facturas = [factura("F-1", "CL-01", date(2026, 4, 1), "10000.00")]
    pagos = [Pago(fecha=date(2026, 5, 2), monto_mxn=Decimal("4000.00"), referencia="DEPOSITO SPEI")]

    conciliacion = conciliar(facturas, pagos, catalogo)
    cartera = analizar(conciliacion, corte=CORTE, rubrica=rubrica)

    assert len(conciliacion.sin_identificar) == 1
    assert cartera.saldo_total_mxn == Decimal("10000.00")
    assert cartera.sin_identificar_mxn == Decimal("4000.00")


def test_la_referencia_bancaria_con_el_folio_si_concilia(catalogo):
    facturas = [factura("F-1", "CL-01", date(2026, 4, 1), "10000.00")]
    pagos = [Pago(fecha=date(2026, 5, 2), monto_mxn=Decimal("10000.00"), referencia="PAGO F-1 ACEROS")]

    conciliacion = conciliar(facturas, pagos, catalogo)

    assert not conciliacion.sin_identificar
    assert conciliacion.saldos["F-1"].liquidada


def test_prioridad_sale_de_regla_no_de_criterio(catalogo, rubrica):
    """§9.1: todo ranking con consecuencia lleva rúbrica versionada, y la versión viaja."""
    facturas = [
        factura("F-CHICA-VIEJA", "CL-01", date(2026, 1, 10), "5000.00"),    # 112 días
        factura("F-GRANDE-NUEVA", "CL-01", date(2026, 4, 20), "40000.00"),  # 12 días
    ]

    cartera = analizar(conciliar(facturas, [], catalogo), corte=CORTE, rubrica=rubrica)
    orden = [fila["factura_id"] for fila in cartera.prioridad]

    assert orden == ["F-GRANDE-NUEVA", "F-CHICA-VIEJA"]     # 40000 + 12*250 gana a 5000 + 112*250
    assert all(fila["rubrica_version"] == rubrica.version for fila in cartera.prioridad)
    assert cartera.rubrica_calibrada is False               # y se dice que aún no está calibrada


def test_la_accion_escala_con_los_dias_vencidos(catalogo, rubrica):
    facturas = [
        factura("F-1", "CL-01", date(2026, 5, 10), "1000.00"),    # vence 9-jun: no vencida
        factura("F-2", "CL-01", date(2026, 4, 20), "1000.00"),    # 12 días
        factura("F-3", "CL-01", date(2026, 3, 20), "1000.00"),    # 43 días
        factura("F-4", "CL-01", date(2026, 1, 10), "1000.00"),    # 112 días
    ]

    cartera = analizar(conciliar(facturas, [], catalogo), corte=CORTE, rubrica=rubrica)
    acciones = {fila["factura_id"]: fila["accion"] for fila in cartera.prioridad}

    assert "F-1" not in acciones                              # lo que no vence no se cobra
    assert acciones["F-2"] == "recordatorio_por_plantilla"
    assert acciones["F-3"] == "gestion_humana"
    assert acciones["F-4"] == "direccion"


def test_dias_credito_del_cliente_mueven_el_vencimiento(catalogo, rubrica):
    """La misma factura, el mismo día: vencida para CL-03 (15 días) y corriente para CL-02 (45)."""
    facturas = [
        factura("F-CL02", "CL-02", date(2026, 5, 1), "10000.00"),
        factura("F-CL03", "CL-03", date(2026, 5, 1), "10000.00"),
    ]

    cartera = analizar(conciliar(facturas, [], catalogo), corte=CORTE, rubrica=rubrica)

    assert cartera.por_cliente["CL-02"]["corriente"] == Decimal("10000.00")
    assert cartera.por_cliente["CL-03"]["1-30"] == Decimal("10000.00")


def test_flujo_esperado_no_cuenta_lo_ya_cobrado(catalogo, rubrica):
    facturas = [
        factura("F-1", "CL-02", date(2026, 5, 20), "10000.00"),   # vence 4-jul
        factura("F-2", "CL-02", date(2026, 5, 21), "20000.00"),   # vence 5-jul
    ]
    pagos = [Pago(fecha=date(2026, 5, 30), monto_mxn=Decimal("10000.00"), factura_id="F-1")]

    cartera = analizar(conciliar(facturas, pagos, catalogo), corte=CORTE, rubrica=rubrica)

    assert sum(cartera.flujo_esperado.values()) == Decimal("20000.00")
    assert cartera.saldo_total_mxn == Decimal("20000.00")


def test_dias_cartera_se_calcula_contra_las_ventas_del_periodo(catalogo, rubrica):
    facturas = [factura("F-1", "CL-01", date(2026, 5, 20), "30000.00")]

    cartera = analizar(
        conciliar(facturas, [], catalogo),
        corte=CORTE,
        rubrica=rubrica,
        ventas_del_periodo_mxn=Decimal("60000.00"),
        dias_del_periodo=30,
    )

    assert cartera.dias_cartera == Decimal("15.0")


def test_una_factura_liquidada_sale_de_la_cartera(catalogo, rubrica):
    facturas = [factura("F-1", "CL-01", date(2026, 1, 10), "10000.00")]
    pagos = [Pago(fecha=date(2026, 5, 30), monto_mxn=Decimal("10000.00"), factura_id="F-1")]

    cartera = analizar(conciliar(facturas, pagos, catalogo), corte=CORTE, rubrica=rubrica)

    assert cartera.saldo_total_mxn == Decimal("0.00")
    assert cartera.prioridad == []
