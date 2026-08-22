"""svc-doc-checklist: presencia, vigencia y pertenencia. Nada de contenido."""

from __future__ import annotations

from datetime import date

import pytest

from services.doc_checklist import (
    Documento,
    ExpedienteIncompleto,
    TipoDeServicioDesconocido,
    cargar_catalogo_documental,
    concepto_respaldado,
    exigir_completo,
    revisar,
)

CORTE = date(2026, 6, 1)


@pytest.fixture
def catalogo_documental():
    return cargar_catalogo_documental()


def doc(tipo: str, trip_id: str = "T-1001", **cambios) -> Documento:
    return Documento(tipo=tipo, trip_id=trip_id, **cambios)


def expediente_de(documentos, tipo_de_servicio="carga_general", catalogo=None, trip_id="T-1001"):
    return revisar(
        trip_id=trip_id,
        tipo_de_servicio=tipo_de_servicio,
        documentos=documentos,
        catalogo=catalogo,
        fecha_corte=CORTE,
    )


def test_expediente_completo_libera_facturacion(catalogo_documental):
    expediente = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod")], catalogo=catalogo_documental
    )

    assert expediente.completo
    assert expediente.listo_para_facturar
    assert exigir_completo(expediente) is expediente


def test_falta_evidencia_de_entrega_bloquea(catalogo_documental):
    """El POD es la diferencia entre un viaje terminado y un viaje cobrable."""
    expediente = expediente_de([doc("orden_de_servicio"), doc("carta_porte")], catalogo=catalogo_documental)

    assert not expediente.listo_para_facturar
    assert [f.tipo for f in expediente.bloqueantes] == ["pod"]

    with pytest.raises(ExpedienteIncompleto) as excinfo:
        exigir_completo(expediente)

    assert "pod" in str(excinfo.value)
    assert excinfo.value.contexto["trip_id"] == "T-1001"


def test_documento_vencido_no_cuenta_como_presente(catalogo_documental):
    """Y se reporta como vencido, no como faltante: hay que renovarlo, no buscarlo."""
    expediente = expediente_de(
        [
            doc("orden_de_servicio"),
            doc("carta_porte"),
            doc("pod"),
            doc("poliza_seguro_carga", vence=date(2026, 5, 31)),
            doc("evidencia_fotografica"),
        ],
        tipo_de_servicio="carga_asegurada",
        catalogo=catalogo_documental,
    )

    assert not expediente.completo
    assert [f.tipo for f in expediente.vencidos] == ["poliza_seguro_carga"]
    assert not expediente.faltantes


def test_la_vigencia_se_deriva_de_la_emision_cuando_no_viene_impresa(catalogo_documental):
    """La póliza declara 365 días de vigencia: una emitida hace dos años ya no vale."""
    vieja = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod"),
         doc("poliza_seguro_carga", emitido=date(2024, 1, 1)), doc("evidencia_fotografica")],
        tipo_de_servicio="carga_asegurada",
        catalogo=catalogo_documental,
    )
    reciente = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod"),
         doc("poliza_seguro_carga", emitido=date(2026, 1, 1)), doc("evidencia_fotografica")],
        tipo_de_servicio="carga_asegurada",
        catalogo=catalogo_documental,
    )

    assert [f.tipo for f in vieja.vencidos] == ["poliza_seguro_carga"]
    assert reciente.completo


def test_documento_de_otro_viaje_se_rechaza(catalogo_documental):
    """La forma más común de que un expediente se vea completo sin estarlo."""
    expediente = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod", trip_id="T-0999")],
        catalogo=catalogo_documental,
    )

    assert not expediente.completo
    assert [d.trip_id for d in expediente.no_corresponden] == ["T-0999"]
    assert [f.tipo for f in expediente.bloqueantes] == ["pod"]


def test_requisitos_dependen_del_tipo_de_servicio(catalogo_documental):
    """Los mismos tres papeles bastan para carga general y no para carga asegurada."""
    documentos = [doc("orden_de_servicio"), doc("carta_porte"), doc("pod")]

    general = expediente_de(documentos, catalogo=catalogo_documental)
    asegurada = expediente_de(documentos, tipo_de_servicio="carga_asegurada", catalogo=catalogo_documental)

    assert general.completo
    assert not asegurada.completo
    assert {f.tipo for f in asegurada.bloqueantes} == {"poliza_seguro_carga", "evidencia_fotografica"}


def test_un_opcional_ausente_no_bloquea(catalogo_documental):
    expediente = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod")], catalogo=catalogo_documental
    )

    assert [f.tipo for f in expediente.faltantes] == ["evidencia_fotografica"]
    assert expediente.completo          # es deseable, no bloqueante


def test_tipo_de_servicio_desconocido_se_rechaza(catalogo_documental):
    with pytest.raises(TipoDeServicioDesconocido):
        expediente_de([doc("pod")], tipo_de_servicio="mudanza_lunar", catalogo=catalogo_documental)


def test_la_estadia_sin_comprobante_no_esta_respaldada(catalogo_documental):
    """La regla que evita cobrar lo que nadie firmó — y perder lo que sí se firmó."""
    sin_comprobante = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod")],
        tipo_de_servicio="dedicado",
        catalogo=catalogo_documental,
    )
    con_comprobante = expediente_de(
        [doc("orden_de_servicio"), doc("carta_porte"), doc("pod"), doc("comprobante_estadia")],
        tipo_de_servicio="dedicado",
        catalogo=catalogo_documental,
    )

    assert not concepto_respaldado(sin_comprobante, "estadia", catalogo_documental)
    assert concepto_respaldado(con_comprobante, "estadia", catalogo_documental)
    assert concepto_respaldado(sin_comprobante, "flete", catalogo_documental)   # el flete no pide papel extra


def test_el_expediente_declara_si_el_catalogo_esta_confirmado(catalogo_documental):
    """Una aprobación contra un catálogo sin confirmar es una aprobación con asterisco."""
    expediente = expediente_de([doc("orden_de_servicio"), doc("carta_porte"), doc("pod")])

    assert expediente.catalogo_version == catalogo_documental.version
    assert expediente.catalogo_confirmado is catalogo_documental.confirmado
