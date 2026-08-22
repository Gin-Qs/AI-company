"""svc-invoicing: las tres puertas —expediente, respaldo y folio— y el timbrado que no se hace solo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.common import Autorizacion
from services.common.errors import EntradaFaltante
from services.doc_checklist import Documento, ExpedienteIncompleto, revisar
from services.invoicing import (
    Concepto,
    ConceptoSinRespaldo,
    EntradaFactura,
    LibroDeFolios,
    Timbrado,
    TimbradoRequiereHumano,
    ViajeYaFacturado,
    armar_borrador,
    cargar_politica,
    conceptos_de_viaje,
    es_persona_moral,
    timbrar,
)
from services.masterdata import cargar_catalogo

FECHA = date(2026, 6, 1)
FLETE = Decimal("26500.00")


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


@pytest.fixture
def libro(tmp_path) -> LibroDeFolios:
    return LibroDeFolios(tmp_path / "folios.jsonl")


def expediente(tipo_de_servicio="carga_general", extra=(), trip_id="T-1001"):
    documentos = [Documento(tipo=t, trip_id=trip_id) for t in ("orden_de_servicio", "carta_porte", "pod")]
    documentos += [Documento(tipo=t, trip_id=trip_id) for t in extra]
    return revisar(
        trip_id=trip_id,
        tipo_de_servicio=tipo_de_servicio,
        documentos=documentos,
        fecha_corte=FECHA,
    )


def entrada(conceptos=None, cliente_id="CL-01", trip_id="T-1001") -> EntradaFactura:
    return EntradaFactura(
        trip_id=trip_id,
        cliente_id=cliente_id,
        conceptos=conceptos if conceptos is not None else conceptos_de_viaje(precio_flete_mxn=FLETE),
        fecha=FECHA,
    )


def test_total_cuadra_con_la_tarifa_aplicada(catalogo, libro):
    """26,500 + IVA 16% − retención 4% de autotransporte = 29,680. Al centavo."""
    borrador = armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    assert borrador.subtotal_mxn == Decimal("26500.00")
    assert borrador.iva_mxn == Decimal("4240.00")
    assert borrador.retencion_mxn == Decimal("1060.00")
    assert borrador.total_mxn == Decimal("29680.00")
    assert borrador.estado == "borrador"


def test_no_factura_viaje_con_expediente_incompleto(catalogo, libro):
    """La puerta se cruza antes de calcular: no hay borrador que revisar después."""
    incompleto = revisar(
        trip_id="T-1001",
        tipo_de_servicio="carga_general",
        documentos=[Documento(tipo="orden_de_servicio", trip_id="T-1001")],
        fecha_corte=FECHA,
    )

    with pytest.raises(ExpedienteIncompleto):
        armar_borrador(entrada(), catalogo, incompleto, libro=libro)

    assert libro.siguiente_folio("A") == 1      # y no se quemó un folio en el intento


def test_demoras_y_estadias_entran_como_concepto(catalogo, libro):
    """El ingreso que la v1 perdía: trabajo hecho que nadie facturaba."""
    conceptos = conceptos_de_viaje(
        precio_flete_mxn=FLETE,
        demoras_horas=Decimal("3"),
        tarifa_demora_mxn_hora=Decimal("450.00"),
        estadias_dias=Decimal("1"),
        tarifa_estadia_mxn_dia=Decimal("2800.00"),
    )
    borrador = armar_borrador(
        entrada(conceptos), catalogo, expediente("dedicado", extra=("comprobante_estadia",)), libro=libro
    )

    assert [c.tipo for c in borrador.conceptos] == ["flete", "demora", "estadia"]
    assert borrador.subtotal_mxn == Decimal("30650.00")     # 26500 + 1350 + 2800


def test_estadia_sin_comprobante_no_se_cobra(catalogo, libro):
    """Cobrar una estadía que nadie firmó es un cargo que el cliente va a rechazar."""
    conceptos = conceptos_de_viaje(
        precio_flete_mxn=FLETE, estadias_dias=Decimal("1"), tarifa_estadia_mxn_dia=Decimal("2800.00")
    )

    with pytest.raises(ConceptoSinRespaldo) as excinfo:
        armar_borrador(entrada(conceptos), catalogo, expediente("dedicado"), libro=libro)

    assert excinfo.value.contexto["requiere"] == "comprobante_estadia"


def test_timbrado_es_hitl_siempre(catalogo, libro):
    """§11.4, regla dura. No hay parámetro que la desactive, y no debe haberlo."""
    borrador = armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    assert borrador.requiere_hitl

    with pytest.raises(TimbradoRequiereHumano) as excinfo:
        timbrar(borrador, libro=libro)

    assert excinfo.value.contexto["requiere"] == "Nay"

    resultado = timbrar(
        borrador,
        autorizacion=Autorizacion(quien="Nay", motivo="expediente revisado", otorgada="2026-06-01"),
        libro=libro,
    )

    assert isinstance(resultado, Timbrado)
    assert resultado.autorizo == "Nay"


def test_sin_pac_no_finge_haber_timbrado(catalogo, libro):
    """Devolver un UUID inventado sería peor que devolver 'pendiente'."""
    politica = cargar_politica()
    borrador = armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    resultado = timbrar(borrador, autorizacion=Autorizacion(quien="Nay", motivo="ok"), libro=libro)

    assert politica.pac is None
    assert resultado.estado == "pendiente_pac"
    assert resultado.uuid is None


def test_folio_no_se_reutiliza(catalogo, libro):
    primero = armar_borrador(entrada(), catalogo, expediente(), libro=libro)
    segundo = armar_borrador(
        entrada(trip_id="T-1002", cliente_id="CL-02"), catalogo, expediente(trip_id="T-1002"), libro=libro
    )

    assert (primero.serie, primero.folio) == ("A", 1)
    assert (segundo.serie, segundo.folio) == ("A", 2)
    assert libro.siguiente_folio("A") == 3


def test_viaje_ya_facturado_no_se_factura_dos_veces(catalogo, libro):
    """Refacturar es un proceso del SAT con reglas propias; no cabe aquí."""
    armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    with pytest.raises(ViajeYaFacturado) as excinfo:
        armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    assert excinfo.value.contexto["folio"] == 1


def test_la_retencion_depende_del_regimen_del_receptor(catalogo, libro):
    """RFC de 12 posiciones = persona moral = retiene 4%. Y queda declarado como supuesto."""
    borrador = armar_borrador(entrada(), catalogo, expediente(), libro=libro)
    supuestos = {s.campo: s for s in borrador.assumptions}

    assert es_persona_moral("ANO910415AB1")
    assert not es_persona_moral("XAXX010101000")     # 13 posiciones: persona física
    assert supuestos["retencion_iva_pct"].valor == Decimal("4.00")
    assert "persona moral" in supuestos["retencion_iva_pct"].detalle


def test_una_factura_sin_conceptos_no_es_una_factura(catalogo, libro):
    with pytest.raises(EntradaFaltante):
        armar_borrador(entrada([]), catalogo, expediente(), libro=libro)


def test_el_expediente_tiene_que_ser_del_mismo_viaje(catalogo, libro):
    from services.common.errors import ErrorDeValidacion

    with pytest.raises(ErrorDeValidacion):
        armar_borrador(entrada(trip_id="T-1002"), catalogo, expediente(trip_id="T-1001"), libro=libro)


def test_el_borrador_declara_con_que_politica_se_armo(catalogo, libro):
    borrador = armar_borrador(entrada(), catalogo, expediente(), libro=libro)

    assert borrador.politica_version
    assert borrador.politica_confirmada is False    # la política sigue sin confirmar con Nay
    assert set(borrador.cifras) == {"subtotal", "iva", "retencion", "total"}
