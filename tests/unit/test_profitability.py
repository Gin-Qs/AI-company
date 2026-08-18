"""svc-profitability: margen, agregacion ponderada, percentiles y contraste de tarifas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.common.errors import ErrorDeValidacion
from services.costing import EntradaCosteo, costear
from services.ingest.registros import Viaje
from services.profitability import (
    agregar,
    contraste_margen_minimo,
    distribucion,
    margen_viaje,
    percentil,
)


def costeo_de(catalogo, **cambios):
    base = {
        "route_id": "R-01",
        "unit_id": "U-01",
        "operador_id": "OP-KM",
        "fuel_price": Decimal("25.00"),
        "trip_id": "T-01",
    }
    base.update(cambios)
    return costear(EntradaCosteo(**base), catalogo)


def viaje_de(trip_id: str, ingreso: str, **cambios) -> Viaje:
    base = dict(
        trip_id=trip_id,
        route_id="R-01",
        unit_id="U-01",
        operador_id="OP-KM",
        cliente_id="CL-01",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 6, 2),
        ingreso_facturado_mxn=Decimal(ingreso),
    )
    base.update(cambios)
    return Viaje(**base)


def test_margen_viaje(catalogo, viaje):
    """Ingreso 30,000 contra costo 21,000: margen 9,000, o 30% del ingreso."""
    resultado = margen_viaje(viaje, costeo_de(catalogo))

    assert resultado.costo_total_mxn == Decimal("21000.00")
    assert resultado.margen_mxn == Decimal("9000.00")
    assert resultado.margen_pct == Decimal("30.00")
    assert resultado.costo_por_km == Decimal("21.0000")
    assert resultado.ingreso_por_km == Decimal("30.0000")
    assert not resultado.en_perdida


def test_viaje_sin_ingreso_bloquea(catalogo):
    """Un viaje sin facturar no es margen -100%: es un hallazgo de facturacion."""
    sin_ingreso = viaje_de("T-01", "0")

    with pytest.raises(ErrorDeValidacion) as excinfo:
        margen_viaje(sin_ingreso, costeo_de(catalogo))

    assert excinfo.value.campo == "ingreso_facturado_mxn"


def test_costeo_de_otro_viaje_bloquea(catalogo):
    with pytest.raises(ErrorDeValidacion):
        margen_viaje(viaje_de("T-99", "30000"), costeo_de(catalogo))


def test_margen_ponderado_no_promedia_porcentajes(catalogo):
    """Un viaje de $30,000 no pesa lo mismo que uno de $3,000, aunque el porcentaje diga otra cosa."""
    grande = margen_viaje(viaje_de("T-01", "30000"), costeo_de(catalogo, trip_id="T-01"))
    chico = margen_viaje(
        viaje_de("T-02", "12000", route_id="R-02"),
        costeo_de(catalogo, trip_id="T-02", route_id="R-02"),
    )

    agregados = {a.clave: a for a in agregar([grande, chico], "cliente")}
    cliente = agregados["CL-01"]

    promedio_simple = (grande.margen_pct + chico.margen_pct) / 2
    ponderado_esperado = (
        (grande.margen_mxn + chico.margen_mxn) / (grande.ingreso_mxn + chico.ingreso_mxn) * 100
    ).quantize(Decimal("0.01"))

    assert cliente.margen_pct == ponderado_esperado
    assert cliente.margen_pct != promedio_simple.quantize(Decimal("0.01"))
    assert cliente.viajes == 2
    assert cliente.margen_mxn == grande.margen_mxn + chico.margen_mxn


def test_percentiles_deterministas():
    valores = [Decimal(v) for v in ("10", "20", "30", "40")]

    assert percentil(valores, Decimal(0)) == Decimal("10.00")
    assert percentil(valores, Decimal(50)) == Decimal("25.00")
    assert percentil(valores, Decimal(25)) == Decimal("17.50")
    assert percentil(valores, Decimal(100)) == Decimal("40.00")
    assert percentil([Decimal("7")], Decimal(50)) == Decimal("7.00")

    with pytest.raises(ErrorDeValidacion):
        percentil([], Decimal(50))
    with pytest.raises(ErrorDeValidacion):
        percentil(valores, Decimal(101))


def test_agregacion_ordena_de_peor_a_mejor(catalogo):
    """Lo que hay que mirar va arriba: primero el peor margen."""
    bueno = margen_viaje(viaje_de("T-01", "40000"), costeo_de(catalogo, trip_id="T-01"))
    malo = margen_viaje(
        viaje_de("T-02", "22000", cliente_id="CL-02"), costeo_de(catalogo, trip_id="T-02")
    )

    agregados = agregar([bueno, malo], "cliente")

    assert [a.clave for a in agregados] == ["CL-02", "CL-01"]
    assert agregados[0].margen_pct < agregados[1].margen_pct


def test_dimension_desconocida_bloquea(catalogo, viaje):
    margen = margen_viaje(viaje, costeo_de(catalogo))

    with pytest.raises(ErrorDeValidacion) as excinfo:
        agregar([margen], "region")

    assert excinfo.value.campo == "dimension"


def test_distribucion_es_el_insumo_de_calibracion(catalogo):
    """La distribucion es lo que se lleva a la mesa para fijar margen objetivo y minimo."""
    margenes = [
        margen_viaje(viaje_de(f"T-0{i}", ingreso), costeo_de(catalogo, trip_id=f"T-0{i}"))
        for i, ingreso in enumerate(("24000", "28000", "30000", "42000"), start=1)
    ]

    d = distribucion(margenes)

    assert d.viajes == 4
    assert d.minimo_pct == Decimal("12.50")  # 24,000 contra 21,000 de costo
    assert d.maximo_pct == Decimal("50.00")
    assert d.mediana_pct == Decimal("27.50")
    assert d.viajes_en_perdida == 0
    assert d.margen_mxn == d.ingreso_mxn - d.costo_mxn

    with pytest.raises(ErrorDeValidacion):
        distribucion([])


def test_viaje_en_perdida_se_marca(catalogo):
    perdida = margen_viaje(viaje_de("T-01", "18000"), costeo_de(catalogo))

    assert perdida.en_perdida
    assert perdida.margen_mxn == Decimal("-3000.00")
    assert distribucion([perdida]).viajes_en_perdida == 1


def test_contraste_margen_minimo(catalogo):
    """Margen real por debajo del minimo de la tabla pre-aprobada: el hallazgo que pide umbrales.md.

    CL-01 tiene tarifa propia con minimo 22%. Con costo de 21,000, facturar
    25,000 deja 16% y dispara la desviacion; facturar 30,000 deja 30% y no.
    """
    bajo = margen_viaje(viaje_de("T-01", "25000"), costeo_de(catalogo, trip_id="T-01"))
    sano = margen_viaje(viaje_de("T-02", "30000"), costeo_de(catalogo, trip_id="T-02"))
    sin_tarifa = margen_viaje(
        viaje_de("T-03", "20000", route_id="R-02"),
        costeo_de(catalogo, trip_id="T-03", route_id="R-02"),
    )

    contraste = contraste_margen_minimo([bajo, sano, sin_tarifa], catalogo)

    assert contraste.resumen() == {
        "evaluados": 3,
        "desviaciones": 1,
        "sin_tarifa_vigente": 1,
        "sin_margen_declarado": 0,
    }
    desviacion = contraste.desviaciones[0]
    assert desviacion.trip_id == "T-01"
    assert desviacion.tarifa_id == "TF-CL01"
    assert desviacion.margen_minimo_pct == Decimal("22.00")
    assert desviacion.margen_real_pct == Decimal("16.00")
    assert desviacion.brecha_pp == Decimal("6.00")
    assert contraste.sin_tarifa == ["T-03"]
