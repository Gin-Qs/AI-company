"""svc-alerts: selecciona qué entra al brief (§9.2); el mensaje es plantilla, no redacción."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.alerts import cargar_reglas, evaluar
from services.ap.cuentas_por_pagar import CuentaPorPagar, analizar as analizar_pagos, conciliar as conciliar_pagos
from services.ar.cartera import Factura, analizar as analizar_cartera, conciliar as conciliar_cartera
from services.ingest.registros import MovimientoBancario
from services.masterdata import cargar_catalogo
from services.profitability.margen import DesviacionTarifa
from services.treasury.posicion import construir as construir_tesoreria

CORTE = date(2026, 6, 1)


@pytest.fixture
def reglas():
    return cargar_reglas()


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


def gasto_diario(dias, monto="-500.00"):
    return [
        MovimientoBancario(
            fecha=date(2026, 5, d), concepto="gasto", monto_mxn=Decimal(monto),
            cuenta="001", referencia="", origen="banco",
        )
        for d in range(1, dias + 1)
    ]


def test_liquidez_por_debajo_del_minimo_genera_alerta_alta(reglas):
    tesoreria = construir_tesoreria(gasto_diario(29), saldo_inicial_mxn="20000.00", corte=CORTE)

    seleccion = evaluar(tesoreria=tesoreria, reglas=reglas)

    alerta = next(a for a in seleccion.alertas if a.tipo == "liquidez")
    assert alerta.severidad == "alta"
    assert alerta.entra_al_brief is True
    assert alerta in seleccion.seleccion_para_el_brief


def test_una_caja_saludable_no_genera_alerta_de_liquidez(reglas):
    tesoreria = construir_tesoreria(gasto_diario(29, "-10.00"), saldo_inicial_mxn="1000000.00", corte=CORTE)

    seleccion = evaluar(tesoreria=tesoreria, reglas=reglas)

    assert not any(a.tipo == "liquidez" for a in seleccion.alertas)


def test_una_desviacion_de_margen_bajo_el_umbral_no_genera_alerta(reglas):
    chica = DesviacionTarifa(
        trip_id="T-1", route_id="R-1", cliente_id="CL-01", tarifa_id="TAR-1",
        margen_real_pct=Decimal("14.5"), margen_minimo_pct=Decimal("15.0"),
        brecha_pp=Decimal("0.5"), ingreso_mxn=Decimal("10000"), precio_tabla_mxn=Decimal("10000"),
    )

    seleccion = evaluar(desviaciones_margen=[chica], reglas=reglas)

    assert not any(a.tipo == "margen" for a in seleccion.alertas)


def test_una_desviacion_de_margen_sobre_el_umbral_genera_alerta_con_la_peor(reglas):
    peor = DesviacionTarifa(
        trip_id="T-PEOR", route_id="R-2", cliente_id="CL-01", tarifa_id="TAR-1",
        margen_real_pct=Decimal("5.0"), margen_minimo_pct=Decimal("15.0"),
        brecha_pp=Decimal("10.0"), ingreso_mxn=Decimal("10000"), precio_tabla_mxn=Decimal("10000"),
    )
    menor = DesviacionTarifa(
        trip_id="T-MENOR", route_id="R-1", cliente_id="CL-01", tarifa_id="TAR-1",
        margen_real_pct=Decimal("12.0"), margen_minimo_pct=Decimal("15.0"),
        brecha_pp=Decimal("3.0"), ingreso_mxn=Decimal("10000"), precio_tabla_mxn=Decimal("10000"),
    )

    seleccion = evaluar(desviaciones_margen=[peor, menor], reglas=reglas)  # ya ordenada por -brecha_pp

    alerta = next(a for a in seleccion.alertas if a.tipo == "margen")
    assert alerta.cifras["peor_trip_id"] == "T-PEOR"
    assert alerta.cifras["viajes_calificados"] == "2"


def test_una_factura_vencida_mas_alla_del_umbral_entra_al_brief(reglas, catalogo):
    facturas = [
        Factura(factura_id="F-1", cliente_id="CL-01", fecha_emision=date(2026, 1, 10), total_mxn=Decimal("5000.00"))
    ]  # 112 dias vencida
    cartera = analizar_cartera(conciliar_cartera(facturas, [], catalogo), corte=CORTE)

    seleccion = evaluar(cartera=cartera, reglas=reglas)

    alerta = next(a for a in seleccion.alertas if a.alerta_id == "cartera-vencida-alta")
    assert alerta.entra_al_brief is True
    assert alerta in seleccion.seleccion_para_el_brief


def test_el_mensaje_de_la_alerta_no_pasa_por_llm(reglas, catalogo):
    """El mensaje es una f-string armada con datos: siempre el mismo texto para los mismos datos."""
    facturas = [
        Factura(factura_id="F-1", cliente_id="CL-01", fecha_emision=date(2026, 1, 10), total_mxn=Decimal("5000.00"))
    ]
    cartera = analizar_cartera(conciliar_cartera(facturas, [], catalogo), corte=CORTE)

    primera = evaluar(cartera=cartera, reglas=reglas)
    segunda = evaluar(cartera=cartera, reglas=reglas)

    assert primera.alertas[0].mensaje == segunda.alertas[0].mensaje


def test_la_severidad_decide_que_entra_al_brief_no_el_agente(reglas, catalogo):
    """cartera-vencida-media es severidad media; severidad_minima_brief es alta: no entra."""
    facturas = [
        # vence 22-abr (30 dias de credito de CL-01): 40 dias vencida a CORTE, cae en el tramo media (15-60)
        Factura(factura_id="F-1", cliente_id="CL-01", fecha_emision=date(2026, 3, 23), total_mxn=Decimal("1000.00"))
    ]
    cartera = analizar_cartera(conciliar_cartera(facturas, [], catalogo), corte=CORTE)

    seleccion = evaluar(cartera=cartera, reglas=reglas)

    media = next(a for a in seleccion.alertas if a.alerta_id == "cartera-vencida-media")
    assert media.severidad == "media"
    assert media.entra_al_brief is False
    assert media not in seleccion.seleccion_para_el_brief


def test_sin_ninguna_entrada_no_hay_alertas(reglas):
    seleccion = evaluar(reglas=reglas)

    assert seleccion.alertas == []
    assert seleccion.seleccion_para_el_brief == []


def test_pagos_vencidos_genera_alerta(reglas):
    cuentas = [
        CuentaPorPagar(
            cuenta_id="CP-1", proveedor_id="PROV-1", fecha_emision=date(2026, 1, 10),
            dias_credito=30, total_mxn=Decimal("2000.00"),
        )
    ]
    pagos = analizar_pagos(conciliar_pagos(cuentas, []), corte=CORTE)

    seleccion = evaluar(pagos=pagos, corte=CORTE, reglas=reglas)

    alerta = next(a for a in seleccion.alertas if a.tipo == "pagos")
    assert alerta.alerta_id == "pagos-vencidos"
    assert alerta.cifras["saldo_vencido_mxn"] == "2000.00"


def test_pagos_por_vencer_dentro_de_la_ventana_genera_alerta(reglas):
    cuentas = [
        CuentaPorPagar(
            cuenta_id="CP-1", proveedor_id="PROV-1", fecha_emision=date(2026, 5, 30),
            dias_credito=3, total_mxn=Decimal("1500.00"),
        )  # vence 2-jun: 1 dia despues del corte, dentro de la ventana de 7 dias
    ]
    pagos = analizar_pagos(conciliar_pagos(cuentas, []), corte=CORTE)

    seleccion = evaluar(pagos=pagos, corte=CORTE, reglas=reglas)

    alerta = next(a for a in seleccion.alertas if a.tipo == "pagos")
    assert alerta.alerta_id == "pagos-por-vencer"
