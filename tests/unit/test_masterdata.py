"""svc-masterdata: carga, integridad referencial y vigencia de tarifas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from services.common.errors import ErrorDeIntegridad, ErrorDeValidacion
from services.masterdata import cargar_catalogo

CLIENTES = "cliente_id,nombre,rfc,dias_credito,activo\nCL-01,Cliente Uno,XAXX010101000,30,si\n"
UNIDADES = (
    "unit_id,placa,tipo,modelo_anio,rendimiento_km_l,costo_adquisicion_mxn,valor_residual_mxn,vida_util_km,"
    "mantenimiento_mxn_km,costo_juego_llantas_mxn,vida_llantas_km,poliza_anual_mxn,km_anuales_esperados,activo\n"
    "U-01,XYZ0001,tracto,2022,2.5,1200000,200000,1000000,2.00,40000,80000,60000,120000,si\n"
)
OPERADORES = (
    "operador_id,nombre,esquema_pago,pago_mxn_km,sueldo_mensual_mxn,viaticos_mxn_dia,"
    "viajes_mensuales_esperados,activo\n"
    "OP-01,Operador Uno,km,3.00,0,500,0,si\n"
)
RUTAS = "route_id,origen,destino,km,casetas_mxn,dias_estimados,activo\nR-01,A,B,1000,2000,2,si\n"
TARIFAS = (
    "tarifa_id,route_id,cliente_id,tipo_unidad,precio_mxn,margen_minimo_pct,vigencia_desde,vigencia_hasta,"
    "version,autorizado_por\n"
    "TF-GEN,R-01,,,30000,18,2026-01-01,,v1,Gabriel\n"
    "TF-CL01,R-01,CL-01,,28000,22,2026-03-01,,v2,Gabriel\n"
)
PARAMETROS = (
    "costos_fijos_mensuales_mxn: 300000\n"
    "base_asignacion_fijos: km\n"
    "km_mensuales_flota: 300000\n"
    "viajes_mensuales_flota: 100\n"
    "moneda: MXN\n"
    "version: v1\n"
)


def escribir_catalogo(destino: Path, **reemplazos: str) -> Path:
    archivos = {
        "clientes.csv": CLIENTES,
        "unidades.csv": UNIDADES,
        "operadores.csv": OPERADORES,
        "rutas.csv": RUTAS,
        "tarifas.csv": TARIFAS,
        "parametros.yaml": PARAMETROS,
    }
    archivos.update(reemplazos)
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in archivos.items():
        (destino / nombre).write_text(contenido, encoding="utf-8")
    return destino


def test_catalogo_carga_completo(tmp_path):
    catalogo = cargar_catalogo(escribir_catalogo(tmp_path / "catalogo"))

    assert catalogo.resumen() == {"clientes": 1, "unidades": 1, "operadores": 1, "rutas": 1, "tarifas": 2}
    assert catalogo.ruta("R-01").km == Decimal("1000")
    assert catalogo.unidad("U-01").rendimiento_km_l == Decimal("2.5000")
    assert catalogo.parametros.base_asignacion_fijos == "km"
    assert catalogo.validar() == []


def test_identificador_duplicado_bloquea(tmp_path):
    duplicadas = RUTAS + "R-01,A,C,1200,2400,2,si\n"

    with pytest.raises(ErrorDeIntegridad) as excinfo:
        cargar_catalogo(escribir_catalogo(tmp_path / "catalogo", **{"rutas.csv": duplicadas}))

    assert "duplicado" in str(excinfo.value)


def test_referencia_de_tarifa_inexistente(tmp_path):
    huerfana = TARIFAS + "TF-X,R-99,,,15000,18,2026-01-01,,v1,Gabriel\n"

    with pytest.raises(ErrorDeIntegridad) as excinfo:
        cargar_catalogo(escribir_catalogo(tmp_path / "catalogo", **{"tarifas.csv": huerfana}))

    assert "ruta inexistente" in str(excinfo.value)


def test_integridad_reporta_todos_los_problemas(tmp_path):
    """El validador junta todos los problemas: corregirlos de a uno cuesta diez rondas."""
    tarifas_rotas = (
        "tarifa_id,route_id,cliente_id,tipo_unidad,precio_mxn,margen_minimo_pct,vigencia_desde,vigencia_hasta,"
        "version,autorizado_por\n"
        "TF-A,R-99,,,30000,18,2026-01-01,,v1,Gabriel\n"
        "TF-B,R-01,CL-99,,30000,18,2026-01-01,,v1,Gabriel\n"
        "TF-C,R-01,,,30000,140,2026-06-01,2026-02-01,v1,Gabriel\n"
    )
    catalogo = cargar_catalogo(
        escribir_catalogo(tmp_path / "catalogo", **{"tarifas.csv": tarifas_rotas}), estricto=False
    )

    problemas = {(p.identificador, p.problema.split(":")[0]) for p in catalogo.validar()}

    assert ("TF-A", "ruta inexistente") in problemas
    assert ("TF-B", "cliente inexistente") in problemas
    assert ("TF-C", "vigencia invertida") in problemas
    assert ("TF-C", "margen minimo fuera del rango [0, 100)") in problemas


def test_tarifa_vigente_gana_la_mas_especifica(tmp_path):
    catalogo = cargar_catalogo(escribir_catalogo(tmp_path / "catalogo"))

    general = catalogo.tarifa_vigente("R-01", date(2026, 6, 1), cliente_id="CL-02")
    del_cliente = catalogo.tarifa_vigente("R-01", date(2026, 6, 1), cliente_id="CL-01")
    antes_de_vigencia = catalogo.tarifa_vigente("R-01", date(2026, 1, 15), cliente_id="CL-01")

    assert general.tarifa_id == "TF-GEN"
    assert del_cliente.tarifa_id == "TF-CL01"
    assert del_cliente.margen_minimo_pct == Decimal("22.0000")
    # En enero la tarifa del cliente aun no existe: gana la general, no la futura.
    assert antes_de_vigencia.tarifa_id == "TF-GEN"
    assert catalogo.tarifa_vigente("R-02", date(2026, 6, 1)) is None


def test_archivo_faltante_es_error_explicito(tmp_path):
    directorio = escribir_catalogo(tmp_path / "catalogo")
    (directorio / "rutas.csv").unlink()

    with pytest.raises(ErrorDeValidacion) as excinfo:
        cargar_catalogo(directorio)

    assert "rutas.csv" in str(excinfo.value)


def test_fila_invalida_senala_numero_de_fila(tmp_path):
    sin_km = "route_id,origen,destino,km,casetas_mxn,dias_estimados,activo\nR-01,A,B,,2000,2,si\n"

    with pytest.raises(ErrorDeValidacion) as excinfo:
        cargar_catalogo(escribir_catalogo(tmp_path / "catalogo", **{"rutas.csv": sin_km}))

    assert "fila 2" in str(excinfo.value)


def test_entidad_inexistente_es_error_de_integridad(tmp_path):
    catalogo = cargar_catalogo(escribir_catalogo(tmp_path / "catalogo"))

    with pytest.raises(ErrorDeIntegridad):
        catalogo.cliente("CL-99")
