"""La Fase 0 completa: catalogo -> ingesta -> costeo -> margen, sobre datos de ejemplo."""

from __future__ import annotations

import json
from decimal import Decimal

from services.cli import main, render
from services.pipeline import ejecutar_fase0


def test_pipeline_fase0(datos_ejemplo):
    reporte = ejecutar_fase0(datos_ejemplo)

    assert reporte.catalogo.resumen() == {
        "clientes": 3,
        "unidades": 3,
        "operadores": 3,
        "rutas": 4,
        "tarifas": 5,
    }
    # 13 viajes en el archivo, uno en ruta: solo se costean los cerrados.
    assert len(reporte.margenes) == 12
    assert reporte.no_costeados == []
    assert all(ingesta.ok for ingesta in reporte.ingestas.values())

    d = reporte.distribucion
    assert d.viajes == 12
    assert d.margen_mxn == d.ingreso_mxn - d.costo_mxn
    assert Decimal("0") < d.ponderado_pct < Decimal("100")
    assert d.p25_pct <= d.mediana_pct <= d.p75_pct


def test_pipeline_produce_las_cuatro_dimensiones(datos_ejemplo):
    reporte = ejecutar_fase0(datos_ejemplo)

    assert set(reporte.agregados) == {"ruta", "cliente", "unidad", "operador"}
    for dimension, agregados in reporte.agregados.items():
        assert agregados, f"{dimension} sin agregados"
        assert sum(a.viajes for a in agregados) == 12
        assert sum(a.margen_mxn for a in agregados) == reporte.distribucion.margen_mxn
        assert agregados == sorted(agregados, key=lambda a: (a.margen_pct, a.clave))


def test_pipeline_costea_con_el_diesel_del_periodo(datos_ejemplo):
    """El precio de diesel es el ponderado del mes del viaje, no el de referencia del catalogo."""
    reporte = ejecutar_fase0(datos_ejemplo)

    assert set(reporte.precios_diesel) == {"2026-05", "2026-06", "2026-07"}
    assert reporte.precios_diesel["2026-05"] < reporte.precios_diesel["2026-07"]

    referencia = reporte.catalogo.parametros.precio_diesel_mxn_litro
    supuestos = {s.campo for costeo in reporte.costeos for s in costeo.assumptions}
    assert referencia is not None
    assert "fuel_price" not in supuestos  # ningun viaje tuvo que caer al precio de referencia


def test_pipeline_usa_los_km_del_gps_cuando_existen(datos_ejemplo):
    reporte = ejecutar_fase0(datos_ejemplo)
    por_viaje = {m.trip_id: m for m in reporte.margenes}

    # T-1001 y T-1007 tienen recorrido GPS; ambos por encima de los 930 km de la ruta.
    assert por_viaje["T-1001"].km == Decimal("948")
    assert por_viaje["T-1007"].km == Decimal("941")
    assert por_viaje["T-1002"].km == Decimal("540")  # sin GPS: los km de la ruta


def test_pipeline_detecta_precios_bajo_el_minimo(datos_ejemplo):
    reporte = ejecutar_fase0(datos_ejemplo)

    assert reporte.contraste.resumen()["sin_tarifa_vigente"] == 0
    assert reporte.contraste.desviaciones, "los datos de ejemplo incluyen viajes bajo el minimo"
    brechas = [d.brecha_pp for d in reporte.contraste.desviaciones]
    assert brechas == sorted(brechas, reverse=True)


def test_pipeline_es_deterministico(datos_ejemplo):
    """Dos corridas sobre los mismos datos dan el mismo JSON, hasta el ultimo centavo."""
    primera = ejecutar_fase0(datos_ejemplo).as_dict()
    segunda = ejecutar_fase0(datos_ejemplo).as_dict()

    assert json.dumps(primera, sort_keys=True) == json.dumps(segunda, sort_keys=True)


def test_cli_escribe_reporte_json(datos_ejemplo, tmp_path, capsys):
    destino = tmp_path / "reporte.json"

    codigo = main(["--datos", str(datos_ejemplo), "--json", str(destino)])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "COSTO Y MARGEN" in salida
    contenido = json.loads(destino.read_text(encoding="utf-8"))
    assert len(contenido["viajes"]) == 12
    assert contenido["distribucion_margen"]["viajes"] == 12
    assert contenido["catalogo"]["rutas"] == 4


def test_cli_falla_con_datos_inexistentes(capsys):
    assert main(["--datos", "data/no-existe"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_render_no_revienta_sin_viajes(datos_ejemplo, tmp_path):
    """Un catalogo valido sin operacion todavia produce reporte, no una excepcion."""
    import shutil

    vacio = tmp_path / "datos"
    shutil.copytree(datos_ejemplo / "catalogo", vacio / "catalogo")
    (vacio / "operacion").mkdir()

    reporte = ejecutar_fase0(vacio)

    assert reporte.margenes == []
    assert "Sin viajes costeados" in render(reporte)
