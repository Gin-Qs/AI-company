"""svc-pricing: la tabla pre-aprobada, el gate de margen mínimo y quién autoriza qué."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.common.errors import EntradaFaltante, ErrorDeValidacion
from services.pricing import (
    AGENTE,
    DIRECCION,
    HUMANO,
    Autorizacion,
    CotizacionBloqueada,
    EntradaCotizacion,
    SinTarifaVigente,
    cargar_politica,
    cotizar,
    dictaminar,
    precio_para_margen,
)
from services.trace import Libro, reconciliar

FECHA = date(2026, 6, 15)


@pytest.fixture
def politica():
    return cargar_politica()


def entrada(**cambios) -> EntradaCotizacion:
    base = {
        "route_id": "R-01",
        "unit_id": "U-01",
        "cliente_id": "CL-02",       # sin tarifa propia: usa la general, mínimo 18%
        "operador_id": "OP-KM",
        "fecha": FECHA,
        "fuel_price": Decimal("25.00"),
    }
    base.update(cambios)
    return EntradaCotizacion(**base)


def test_cotizacion_de_tabla_la_puede_hacer_el_agente(catalogo, politica):
    """authority-gate: 'tarifa dentro de la tabla vigente y margen >= minimo de la ruta'."""
    cotizacion = cotizar(entrada(), catalogo, politica=politica)

    assert cotizacion.precio_mxn == Decimal("30000.00")      # el precio de la tabla, sin tocar
    assert cotizacion.costo_mxn == Decimal("21000.00")       # el costo que da svc-costing
    assert cotizacion.margen_mxn == Decimal("9000.00")
    assert cotizacion.margen_pct == Decimal("30.00")
    assert cotizacion.margen_minimo_pct == Decimal("18.00")
    assert cotizacion.dentro_de_tabla
    assert cotizacion.nivel_autorizacion == AGENTE
    assert not cotizacion.requiere_humano
    assert dictaminar(cotizacion, politica).ok


def test_la_tarifa_del_cliente_gana_a_la_general(catalogo, politica):
    """CL-01 tiene su propio renglón: precio menor y mínimo más alto."""
    cotizacion = cotizar(entrada(cliente_id="CL-01"), catalogo, politica=politica)

    assert cotizacion.tarifa_id == "TF-CL01"
    assert cotizacion.precio_mxn == Decimal("28000.00")
    assert cotizacion.margen_minimo_pct == Decimal("22.00")


def test_descuento_operativo_va_a_humano(catalogo, politica):
    """Dentro de tabla pero con negociación: lo cierra Ana, no el agente."""
    cotizacion = cotizar(entrada(descuento_pct=Decimal("4")), catalogo, politica=politica)

    assert cotizacion.precio_mxn == Decimal("28800.00")
    assert cotizacion.descuento_pct == Decimal("4.00")
    assert not cotizacion.dentro_de_tabla
    assert cotizacion.nivel_autorizacion == HUMANO
    assert cotizacion.quien_autoriza == "Ana"


def test_descuento_sobre_el_umbral_escala_a_direccion(catalogo, politica):
    """El umbral de 5% sí está calibrado: sale del organigrama firmado."""
    cotizacion = cotizar(entrada(descuento_pct=Decimal("7")), catalogo, politica=politica)

    assert cotizacion.nivel_autorizacion == DIRECCION
    assert cotizacion.quien_autoriza == "Gabriel"
    assert "7.00%" in cotizacion.motivo_gate
    assert not dictaminar(cotizacion, politica).ok       # svc-validation lo marca también


def test_cotizacion_bajo_el_minimo_no_se_genera(catalogo, politica):
    """§4.1: no puede generarse. No es una advertencia en el texto: es un bloqueo."""
    with pytest.raises(CotizacionBloqueada) as excinfo:
        cotizar(entrada(descuento_pct=Decimal("20")), catalogo, politica=politica)

    error = excinfo.value
    assert error.codigo == "PRICING-BLOQUEADA"
    assert error.contexto["requiere"] == "Gabriel"
    assert Decimal(error.contexto["margen_pct"]) < Decimal(error.contexto["margen_minimo_pct"])


def test_autorizacion_de_direccion_permite_la_excepcion(catalogo, politica):
    """Dirección puede autorizar por debajo del mínimo, y queda escrito en la cotización."""
    permiso = Autorizacion(quien="Gabriel", motivo="cliente ancla, viaje de retorno vacío", otorgada="2026-06-15")

    cotizacion = cotizar(entrada(descuento_pct=Decimal("20")), catalogo, politica=politica, autorizacion=permiso)

    assert cotizacion.margen_pct < cotizacion.margen_minimo_pct
    assert cotizacion.nivel_autorizacion == DIRECCION
    assert cotizacion.autorizacion.quien == "Gabriel"
    assert "retorno vacío" in cotizacion.autorizacion.motivo


def test_precio_propuesto_se_traduce_a_descuento(catalogo, politica):
    cotizacion = cotizar(entrada(precio_propuesto_mxn=Decimal("28500.00")), catalogo, politica=politica)

    assert cotizacion.precio_mxn == Decimal("28500.00")
    assert cotizacion.descuento_pct == Decimal("5.00")
    assert cotizacion.nivel_autorizacion == HUMANO


def test_precio_y_descuento_a_la_vez_se_rechaza(catalogo, politica):
    with pytest.raises(ErrorDeValidacion):
        cotizar(
            entrada(precio_propuesto_mxn=Decimal("28500.00"), descuento_pct=Decimal("5")),
            catalogo,
            politica=politica,
        )


def test_sin_tarifa_vigente_no_cotiza(catalogo, politica):
    """R-02 no tiene renglón en la tabla: cotizar fuera de tabla lo autoriza Dirección."""
    with pytest.raises(SinTarifaVigente) as excinfo:
        cotizar(entrada(route_id="R-02"), catalogo, politica=politica)

    assert "Gabriel" in str(excinfo.value)


def test_tarifa_sin_margen_minimo_bloquea(catalogo, politica):
    """Sin mínimo declarado y con el umbral global sin calibrar, no hay gate — y sin gate no se cotiza."""
    sin_minimo = [t for t in catalogo.tarifas if t.tarifa_id == "TF-GEN"][0]
    catalogo.tarifas = [
        type(sin_minimo)(**{**sin_minimo.__dict__, "margen_minimo_pct": None, "cliente_id": None})
    ]

    with pytest.raises(EntradaFaltante) as excinfo:
        cotizar(entrada(), catalogo, politica=politica)

    assert "umbrales.md" in str(excinfo.value)


def test_precio_para_margen_objetivo():
    """El margen se calcula sobre el precio, no sobre el costo: 21,000 al 30% son 30,000."""
    assert precio_para_margen(Decimal("21000"), Decimal("30")) == Decimal("30000.00")
    assert precio_para_margen(Decimal("21000"), Decimal("0")) == Decimal("21000.00")

    with pytest.raises(ErrorDeValidacion):
        precio_para_margen(Decimal("21000"), Decimal("100"))


def test_las_cifras_quedan_listas_para_trace(catalogo, politica):
    """Cada número de la cotización nace con su origen, para que el entregable reconcilie."""
    libro = Libro(trace_id="TR-20260615-001")

    cotizacion = cotizar(entrada(), catalogo, politica=politica, libro=libro)

    assert set(cotizacion.cifras) == {
        "precio",
        "costo",
        "costo_por_km",
        "margen",
        "margen_pct",
        "margen_minimo_pct",
    }
    assert set(cotizacion.fuentes) == set(cotizacion.cifras)
    assert libro.por_nombre("precio").servicio == "svc-pricing"
    assert libro.por_nombre("costo_por_km").servicio == "svc-costing"

    entregable = {"cifras": cotizacion.cifras, "fuentes": cotizacion.fuentes}
    assert reconciliar(entregable, libro).ok


def test_los_supuestos_del_costeo_viajan_en_la_cotizacion(catalogo, politica):
    cotizacion = cotizar(entrada(), catalogo, politica=politica)

    campos = {s.campo for s in cotizacion.assumptions}
    assert "driver_cost" in campos          # se derivó del esquema del operador
    assert cotizacion.costeo.total_trip_cost == cotizacion.costo_mxn
