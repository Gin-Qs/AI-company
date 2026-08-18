"""svc-costing. Los tres primeros son los que declara el contrato de la seccion 10.2."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.common.errors import EntradaFaltante, ErrorDeValidacion
from services.costing import CONCEPTOS_VARIABLES, EntradaCosteo, costear, costear_viaje


def entrada(**cambios) -> EntradaCosteo:
    base = {"route_id": "R-01", "unit_id": "U-01", "operador_id": "OP-KM", "fuel_price": Decimal("25.00")}
    base.update(cambios)
    return EntradaCosteo(**base)


def test_cost_per_km(catalogo):
    """1000 km a 2.5 km/l con diesel a $25: el costo por km es exactamente $21.00.

    diesel 10,000 + casetas 2,000 + operador 4,000 + mantenimiento 2,000 +
    llantas 500 + seguro 500 + depreciacion 1,000 = 20,000 variable,
    mas 1,000 de fijos asignados = 21,000 / 1000 km.
    """
    resultado = costear(entrada(), catalogo)

    assert resultado.km == Decimal("1000")
    assert resultado.desglose["diesel"] == Decimal("10000.00")
    assert resultado.desglose["casetas"] == Decimal("2000.00")
    assert resultado.desglose["operador"] == Decimal("4000.00")
    assert resultado.desglose["mantenimiento"] == Decimal("2000.00")
    assert resultado.desglose["llantas"] == Decimal("500.00")
    assert resultado.desglose["seguro"] == Decimal("500.00")
    assert resultado.desglose["depreciacion"] == Decimal("1000.00")
    assert resultado.variable_cost == Decimal("20000.00")
    assert resultado.fixed_allocated_cost == Decimal("1000.00")
    assert resultado.total_trip_cost == Decimal("21000.00")
    assert resultado.cost_per_km == Decimal("21.0000")
    assert resultado.variable_cost_per_km == Decimal("20.0000")


def test_missing_fuel_price(catalogo):
    """Sin precio de diesel y sin precio de referencia, el calculo se detiene."""
    with pytest.raises(EntradaFaltante) as excinfo:
        costear(entrada(fuel_price=None), catalogo)

    assert excinfo.value.campo == "fuel_price"
    assert excinfo.value.codigo == "SVC-INPUT-MISSING"


def test_missing_fuel_price_usa_referencia_del_catalogo_y_lo_declara(catalogo):
    """Si el catalogo trae precio de referencia, se usa, pero queda escrito como supuesto."""
    catalogo.parametros = catalogo.parametros.__class__(
        costos_fijos_mensuales_mxn=catalogo.parametros.costos_fijos_mensuales_mxn,
        base_asignacion_fijos="km",
        km_mensuales_flota=catalogo.parametros.km_mensuales_flota,
        viajes_mensuales_flota=catalogo.parametros.viajes_mensuales_flota,
        precio_diesel_mxn_litro=Decimal("25.0000"),
    )

    resultado = costear(entrada(fuel_price=None), catalogo)

    supuesto = next(s for s in resultado.assumptions if s.campo == "fuel_price")
    assert supuesto.fuente == "parametro"
    assert resultado.cost_per_km == Decimal("21.0000")


def test_negative_distance_blocked(catalogo):
    """Una distancia no positiva bloquea: dividir entre cero produce un numero que alguien cotiza."""
    with pytest.raises(ErrorDeValidacion) as negativa:
        costear(entrada(km=Decimal("-100")), catalogo)
    assert negativa.value.campo == "km"

    with pytest.raises(ErrorDeValidacion):
        costear(entrada(km=Decimal("0")), catalogo)


def test_desglose_suma_total(catalogo):
    resultado = costear(entrada(), catalogo)
    variable = sum(resultado.desglose[c] for c in CONCEPTOS_VARIABLES)

    assert variable == resultado.variable_cost
    assert resultado.variable_cost + resultado.fixed_allocated_cost == resultado.total_trip_cost


def test_supuestos_declarados(catalogo):
    """Todo lo que el servicio no recibio y tuvo que derivar queda listado (seccion 7.1)."""
    resultado = costear(entrada(), catalogo)
    campos = {s.campo for s in resultado.assumptions}

    assert {"km", "dias", "tolls", "driver_cost", "tire_factor", "insurance_factor"} <= campos
    assert all(s.detalle for s in resultado.assumptions)

    completa = costear(
        entrada(
            km=Decimal("1000"),
            dias=Decimal("2"),
            tolls=Decimal("2000"),
            driver_cost=Decimal("4000"),
            maintenance_factor=Decimal("2"),
            tire_factor=Decimal("0.5"),
            insurance_factor=Decimal("0.5"),
            fixed_cost_allocation=Decimal("1000"),
        ),
        catalogo,
    )
    # Con todo explicito solo queda el supuesto de depreciacion, que siempre sale del catalogo.
    assert {s.campo for s in completa.assumptions} == {"depreciacion_mxn_km"}
    assert completa.total_trip_cost == Decimal("21000.00")


def test_entrada_explicita_gana_al_catalogo(catalogo):
    resultado = costear(entrada(tolls=Decimal("3500.00")), catalogo)

    assert resultado.desglose["casetas"] == Decimal("3500.00")
    assert "tolls" not in {s.campo for s in resultado.assumptions}
    assert resultado.total_trip_cost == Decimal("22500.00")


def test_operador_por_esquema_mixto(catalogo):
    """Mixto: pago por km + sueldo prorrateado entre viajes esperados + viaticos."""
    resultado = costear(entrada(operador_id="OP-MIX"), catalogo)

    # 1.00 x 1000 + 10,000 / 10 + 400 x 2 dias
    assert resultado.desglose["operador"] == Decimal("2800.00")


def test_sueldo_fijo_sin_viajes_esperados_bloquea(catalogo):
    operador = catalogo.operadores["OP-MIX"]
    catalogo.operadores["OP-MIX"] = operador.__class__(
        operador_id=operador.operador_id,
        nombre=operador.nombre,
        esquema_pago="fijo",
        pago_mxn_km=Decimal("0"),
        sueldo_mensual_mxn=Decimal("10000.00"),
        viaticos_mxn_dia=Decimal("400.00"),
        viajes_mensuales_esperados=Decimal("0"),
    )

    with pytest.raises(EntradaFaltante) as excinfo:
        costear(entrada(operador_id="OP-MIX"), catalogo)
    assert excinfo.value.campo == "viajes_mensuales_esperados"


def test_fijos_por_viaje(catalogo):
    """Con base 'viaje', los fijos se reparten entre viajes de flota, no entre km."""
    parametros = catalogo.parametros
    catalogo.parametros = parametros.__class__(
        costos_fijos_mensuales_mxn=Decimal("300000.00"),
        base_asignacion_fijos="viaje",
        km_mensuales_flota=parametros.km_mensuales_flota,
        viajes_mensuales_flota=Decimal("100"),
        precio_diesel_mxn_litro=None,
    )

    resultado = costear(entrada(), catalogo)

    assert resultado.fixed_allocated_cost == Decimal("3000.00")
    assert resultado.total_trip_cost == Decimal("23000.00")


def test_costear_viaje_usa_km_reales(catalogo, viaje):
    """Los km del GPS desplazan a los del catalogo, y el costo por km lo refleja."""
    del_catalogo = costear_viaje(viaje, catalogo, fuel_price=Decimal("25.00"))
    con_gps = costear_viaje(viaje, catalogo, fuel_price=Decimal("25.00"), km_reales=Decimal("1100"))

    assert del_catalogo.km == Decimal("1000")
    assert con_gps.km == Decimal("1100")
    assert con_gps.total_trip_cost > del_catalogo.total_trip_cost
    assert con_gps.trip_id == "T-01"


def test_unidad_inexistente_es_error_de_integridad(catalogo):
    from services.common.errors import ErrorDeIntegridad

    with pytest.raises(ErrorDeIntegridad):
        costear(entrada(unit_id="U-99"), catalogo)
