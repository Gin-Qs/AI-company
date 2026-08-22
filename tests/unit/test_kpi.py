"""svc-kpi: empaqueta números que ya calculó otro servicio, con semáforo contra meta."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.kpi import KPIDesconocido, cargar_catalogo, construir_tablero


@pytest.fixture
def catalogo():
    return cargar_catalogo()


def test_un_kpi_sin_catalogo_declarado_no_se_reporta(catalogo):
    with pytest.raises(KPIDesconocido):
        construir_tablero({"kpi_que_no_existe": 10}, periodo="2026-06", catalogo=catalogo)


def test_el_semaforo_compara_contra_la_meta_declarada(catalogo):
    """margen_ponderado_pct: mayor_mejor, meta 15.0, tolerancia 10%."""
    tablero = construir_tablero(
        {"margen_ponderado_pct": Decimal("18.0")}, periodo="2026-06", catalogo=catalogo
    )
    assert tablero.indicadores[0].estado == "verde"

    tablero = construir_tablero(
        {"margen_ponderado_pct": Decimal("14.0")}, periodo="2026-06", catalogo=catalogo
    )  # dentro del 10% bajo la meta (>= 13.5)
    assert tablero.indicadores[0].estado == "amarillo"

    tablero = construir_tablero(
        {"margen_ponderado_pct": Decimal("10.0")}, periodo="2026-06", catalogo=catalogo
    )
    assert tablero.indicadores[0].estado == "rojo"


def test_el_semaforo_funciona_tambien_para_menor_mejor(catalogo):
    """dias_cartera_dso: menor_mejor, meta 30."""
    tablero = construir_tablero({"dias_cartera_dso": Decimal("25")}, periodo="2026-06", catalogo=catalogo)
    assert tablero.indicadores[0].estado == "verde"

    tablero = construir_tablero({"dias_cartera_dso": Decimal("45")}, periodo="2026-06", catalogo=catalogo)
    assert tablero.indicadores[0].estado == "rojo"


def test_el_tablero_agrupa_por_departamento(catalogo):
    tablero = construir_tablero(
        {
            "margen_ponderado_pct": Decimal("15.0"),
            "tasa_rechazo_ingesta_pct": Decimal("2.0"),
        },
        periodo="2026-06",
        catalogo=catalogo,
    )

    agrupado = tablero.por_departamento()

    assert set(agrupado) == {"02-finanzas-contabilidad-administracion", "05-tecnologia-datos-innovacion"}
    assert len(agrupado["02-finanzas-contabilidad-administracion"]) == 1


def test_un_kpi_no_recalcula_el_numero_solo_lo_empaqueta(catalogo):
    """El valor que entra es exactamente el valor que sale: no hay transformación."""
    tablero = construir_tablero({"dias_de_caja": Decimal("77.3")}, periodo="2026-06", catalogo=catalogo)

    assert tablero.indicadores[0].valor == Decimal("77.3")
    assert tablero.indicadores[0].fuente == "svc-treasury"
