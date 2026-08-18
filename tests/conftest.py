"""Fixtures comunes.

El catalogo de pruebas usa cifras redondas a proposito: con 1000 km, 2.5 km/l
y diesel a $25, el costo por km da exactamente $21.00. Un test que falla
senala la formula que se rompio, no un problema de redondeo.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from services.ingest.registros import Viaje
from services.masterdata.catalogo import Catalogo
from services.masterdata.models import Cliente, Operador, Parametros, Ruta, Tarifa, Unidad

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def raiz() -> Path:
    return RAIZ


@pytest.fixture
def oficina_temporal(tmp_path, monkeypatch):
    """Redirige encargos, bitácora, memorias y prompts a un directorio desechable.

    Sin esto, correr las pruebas ensuciaría la oficina real: encargos de mentira en el backlog
    del ERP y notas falsas en la memoria de un agente. La memoria es un archivo versionado;
    un test no tiene por qué escribir en ella.
    """
    from agents import memoria as memoria_mod
    from agents import runtime
    from office import bitacora
    from office import encargos as encargos_mod

    from office import estado as estado_mod

    monkeypatch.setattr(encargos_mod, "DIRECTORIO", tmp_path / "encargos")
    monkeypatch.setattr(bitacora, "ARCHIVO", tmp_path / "bitacora.jsonl")
    monkeypatch.setattr(memoria_mod, "DIRECTORIO", tmp_path / "memoria")
    monkeypatch.setattr(runtime, "DIR_PROMPTS", tmp_path / "prompts")
    # La pausa es estado real de la oficina. Las pruebas del flujo corren sobre una oficina
    # abierta; que la pausa detiene las convocatorias lo cubre su propio test.
    monkeypatch.setattr(estado_mod, "PAUSA", tmp_path / "sin-pausa.yaml")
    (tmp_path / "memoria").mkdir()
    return tmp_path


@pytest.fixture
def datos_ejemplo() -> Path:
    return RAIZ / "data" / "ejemplo"


def _unidad(unit_id: str = "U-01") -> Unidad:
    return Unidad(
        unit_id=unit_id,
        placa="XYZ0001",
        tipo="tracto",
        rendimiento_km_l=Decimal("2.5"),
        costo_adquisicion_mxn=Decimal("1200000.00"),
        valor_residual_mxn=Decimal("200000.00"),
        vida_util_km=Decimal("1000000"),  # depreciacion = 1.00 / km
        mantenimiento_mxn_km=Decimal("2.0000"),
        costo_juego_llantas_mxn=Decimal("40000.00"),
        vida_llantas_km=Decimal("80000"),  # llantas = 0.50 / km
        poliza_anual_mxn=Decimal("60000.00"),
        km_anuales_esperados=Decimal("120000"),  # seguro = 0.50 / km
        modelo_anio=2022,
    )


@pytest.fixture
def catalogo() -> Catalogo:
    return Catalogo(
        clientes={
            "CL-01": Cliente(cliente_id="CL-01", nombre="Cliente Uno", rfc="XAXX010101000", dias_credito=30),
            "CL-02": Cliente(cliente_id="CL-02", nombre="Cliente Dos", rfc="XAXX010101001", dias_credito=45),
        },
        unidades={"U-01": _unidad(), "U-02": _unidad("U-02")},
        operadores={
            "OP-KM": Operador(
                operador_id="OP-KM",
                nombre="Operador por km",
                esquema_pago="km",
                pago_mxn_km=Decimal("3.0000"),
                sueldo_mensual_mxn=Decimal("0.00"),
                viaticos_mxn_dia=Decimal("500.00"),
                viajes_mensuales_esperados=Decimal("0"),
            ),
            "OP-MIX": Operador(
                operador_id="OP-MIX",
                nombre="Operador mixto",
                esquema_pago="mixto",
                pago_mxn_km=Decimal("1.0000"),
                sueldo_mensual_mxn=Decimal("10000.00"),
                viaticos_mxn_dia=Decimal("400.00"),
                viajes_mensuales_esperados=Decimal("10"),
            ),
        },
        rutas={
            "R-01": Ruta(
                route_id="R-01",
                origen="A",
                destino="B",
                km=Decimal("1000"),
                casetas_mxn=Decimal("2000.00"),
                dias_estimados=Decimal("2"),
            ),
            "R-02": Ruta(
                route_id="R-02",
                origen="B",
                destino="C",
                km=Decimal("500"),
                casetas_mxn=Decimal("900.00"),
                dias_estimados=Decimal("1"),
            ),
        },
        tarifas=[
            Tarifa(
                tarifa_id="TF-GEN",
                route_id="R-01",
                precio_mxn=Decimal("30000.00"),
                margen_minimo_pct=Decimal("18.0000"),
                vigencia_desde=date(2026, 1, 1),
                vigencia_hasta=None,
                version="v1",
            ),
            Tarifa(
                tarifa_id="TF-CL01",
                route_id="R-01",
                cliente_id="CL-01",
                precio_mxn=Decimal("28000.00"),
                margen_minimo_pct=Decimal("22.0000"),
                vigencia_desde=date(2026, 3, 1),
                vigencia_hasta=None,
                version="v2",
            ),
        ],
        parametros=Parametros(
            costos_fijos_mensuales_mxn=Decimal("300000.00"),
            base_asignacion_fijos="km",
            km_mensuales_flota=Decimal("300000"),  # fijos = 1.00 / km
            viajes_mensuales_flota=Decimal("100"),
            precio_diesel_mxn_litro=None,
        ),
    )


@pytest.fixture
def viaje() -> Viaje:
    return Viaje(
        trip_id="T-01",
        route_id="R-01",
        unit_id="U-01",
        operador_id="OP-KM",
        cliente_id="CL-01",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 6, 2),
        ingreso_facturado_mxn=Decimal("30000.00"),
        estatus="cerrado",
    )
