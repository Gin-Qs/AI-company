"""El flujo completo de la Fase 2: del viaje cerrado al peso cobrado.

Los cinco servicios de la fase trabajando juntos sobre el catálogo real de `data/ejemplo`, sin
agente y sin LLM. Cuando `D3-05` y `D2-04` se enciendan, esto es exactamente lo que van a
orquestar — y lo único que el modelo añadirá es la redacción, nunca una cifra ni una decisión.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.ar import Factura, Pago, analizar, conciliar
from services.cfdi_validate import validar_cfdi
from services.common import Autorizacion
from services.doc_checklist import Documento, ExpedienteIncompleto, revisar
from services.invoicing import (
    EntradaFactura,
    LibroDeFolios,
    armar_borrador,
    conceptos_de_viaje,
    timbrar,
)
from services.masterdata import cargar_catalogo
from services.notify import enviar, render
from services.runlog import RunLog, entregar
from services.trace import Libro, exigir_reconciliacion
from services.validation import exigir

FECHA = date(2026, 6, 1)
FLETE = Decimal("26500.00")


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


@pytest.fixture
def runlog(tmp_path) -> RunLog:
    return RunLog(tmp_path / "runlog.jsonl")


@pytest.fixture
def libro_folios(tmp_path) -> LibroDeFolios:
    return LibroDeFolios(tmp_path / "folios.jsonl")


def documentos(*tipos, trip_id="T-1001"):
    return [Documento(tipo=t, trip_id=trip_id) for t in tipos]


def entregable_de(borrador, dictamen, fuentes: dict[str, str]) -> dict:
    """El entregable que D2-04 redactaría, con el contrato de §7.1 puesto.

    `fuentes` liga cada cifra citada con su asiento en el libro de svc-trace. Sin ese enlace
    el entregable no cuadra, y no cuadrar es motivo suficiente para no entregarlo.
    """
    return {
        "decision_solicitada": f"autorizar el timbrado del comprobante {borrador.identificador}",
        "fuentes": fuentes,
        "cifras": {
            "subtotal": borrador.subtotal_mxn,
            "iva": borrador.iva_mxn,
            "retencion": borrador.retencion_mxn,
            "total": borrador.total_mxn,
        },
        "supuestos": [s.detalle for s in borrador.assumptions],
        "confianza": {
            "nivel": "media",
            "limitado_por": f"el catalogo del SAT es un subconjunto ({dictamen.catalogo_version}) "
            f"y no sustituye la validacion XSD",
        },
        "opciones": ["timbrar hoy", "esperar a que el cliente confirme el domicilio fiscal"],
        "si_no_respondes": "el viaje queda sin facturar y el credito del cliente empieza a correr tarde; 1 dia habil",
        # Sin identificadores en la prosa: svc-trace persigue todo numero suelto, y el folio
        # de un viaje no es una cifra con origen. Va en decision_solicitada, que no se escanea.
        "resumen": (
            f"Comprobante por ${borrador.total_mxn}, con IVA de ${borrador.iva_mxn} y "
            f"retencion de ${borrador.retencion_mxn}."
        ),
    }


def test_flujo_de_cierre_a_cobro(catalogo, runlog, libro_folios, raiz):
    """Expediente completo → borrador → CFDI válido → timbrado con firma → cartera."""
    # 1. D3-05 abre el caso al cerrar el viaje.
    caso = runlog.abrir_caso(tipo="cierre_de_viaje", referencia="T-1001", criticidad="media", actor="D3-05")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D3-05")

    # 2. La primera puerta: el expediente.
    expediente = revisar(
        trip_id="T-1001",
        tipo_de_servicio="carga_general",
        documentos=documentos("orden_de_servicio", "carta_porte", "pod"),
        fecha_corte=FECHA,
    )
    runlog.registrar_paso(
        caso.trace_id,
        actor="svc-doc-checklist",
        tipo="llamada_servicio",
        salidas={"completo": str(expediente.completo)},
        versiones={"catalogo_documental": expediente.catalogo_version},
    )
    assert expediente.listo_para_facturar

    # 3. D2-04 arma el comprobante. El precio ya venía de la Fase 1; aquí sólo se factura.
    trazas = Libro(trace_id=caso.trace_id)
    borrador = armar_borrador(
        EntradaFactura(
            trip_id="T-1001",
            cliente_id="CL-01",
            conceptos=conceptos_de_viaje(precio_flete_mxn=FLETE),
            fecha=FECHA,
            trace_id=caso.trace_id,
        ),
        catalogo,
        expediente,
        libro=libro_folios,
    )
    fuentes = {
        nombre: trazas.registrar(
            nombre, valor, servicio="svc-invoicing", consulta=f"borrador {borrador.identificador}"
        ).cifra_id
        for nombre, valor in borrador.cifras.items()
    }

    # 4. La segunda puerta: el comprobante contra las reglas del SAT.
    xml = (raiz / "tests" / "fixtures" / "cfdi_valido.xml").read_text(encoding="utf-8")
    dictamen = validar_cfdi(xml, rfc_receptor_esperado=borrador.receptor_rfc)
    runlog.registrar_paso(
        caso.trace_id,
        actor="svc-cfdi-validate",
        tipo="validacion",
        resultado="ok" if dictamen.ok else "fallo",
        versiones={"catalogo_sat": dictamen.catalogo_version},
    )
    assert dictamen.ok

    # 5. Las dos puertas del entregable: reglas y reconciliación de cifras.
    entregable = entregable_de(borrador, dictamen, fuentes)
    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    assert exigir(entregable, "entregable").ok
    assert exigir_reconciliacion(entregable, trazas).verificadas == len(borrador.cifras)

    # 6. El gate: ACT-DOC-S es HITL siempre. El caso espera a Nay, con SLA corriendo.
    runlog.transicionar(caso.trace_id, "esperando_humano", actor="Nay", motivo="ACT-DOC-S: timbrado")
    assert runlog.progreso(caso.trace_id).vence_en is not None

    timbrado = timbrar(
        borrador,
        autorizacion=Autorizacion(quien="Nay", motivo="expediente y CFDI revisados", otorgada="2026-06-01"),
        libro=libro_folios,
    )
    assert timbrado.autorizo == "Nay"

    final = entregar(runlog, caso.trace_id, actor="D2-04")
    assert final.estado == "entregado"

    # 7. La factura entra a cartera y el cobro la saca.
    factura = Factura(
        factura_id=borrador.identificador,
        cliente_id="CL-01",
        fecha_emision=FECHA,
        total_mxn=borrador.total_mxn,
        trip_id="T-1001",
    )
    sin_cobrar = analizar(conciliar([factura], [], catalogo), corte=date(2026, 7, 15))
    cobrada = analizar(
        conciliar([factura], [Pago(date(2026, 7, 1), borrador.total_mxn, factura_id=factura.factura_id)], catalogo),
        corte=date(2026, 7, 15),
    )

    assert sin_cobrar.saldo_vencido_mxn == borrador.total_mxn     # venció el 1-jul, 30 días de crédito
    assert cobrada.saldo_total_mxn == Decimal("0.00")


def test_sin_expediente_no_hay_factura_y_el_caso_pide_el_documento(catalogo, runlog, libro_folios):
    """El camino que importa: el viaje se queda sin facturar y alguien recibe el pedido."""
    caso = runlog.abrir_caso(tipo="cierre_de_viaje", referencia="T-1002", criticidad="media", actor="D3-05")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D3-05")

    expediente = revisar(
        trip_id="T-1002",
        tipo_de_servicio="carga_general",
        documentos=documentos("orden_de_servicio", "carta_porte", trip_id="T-1002"),
        fecha_corte=FECHA,
    )

    with pytest.raises(ExpedienteIncompleto):
        armar_borrador(
            EntradaFactura(
                trip_id="T-1002",
                cliente_id="CL-02",
                conceptos=conceptos_de_viaje(precio_flete_mxn=Decimal("15900.00")),
                fecha=FECHA,
            ),
            catalogo,
            expediente,
            libro=libro_folios,
        )

    # D3-05 pide el faltante con plantilla fija: ningún LLM redacta este mensaje.
    faltante = expediente.bloqueantes[0]
    mensaje = render(
        "documento_faltante",
        {"nombre": "Elias", "trip_id": "T-1002", "documento": faltante.detalle},
        destinatario_id="OP-01",
        catalogo=catalogo,
    )
    envio = enviar(mensaje, runlog=runlog, trace_id=caso.trace_id)
    bloqueado = runlog.transicionar(caso.trace_id, "bloqueado", actor="D3-05", motivo=f"falta {faltante.tipo}")

    assert mensaje.paso_por_llm is False
    assert envio.estado == "registrado_para_envio_humano"
    assert bloqueado.estado == "bloqueado"
    assert libro_folios.siguiente_folio("A") == 1        # no se quemó un folio
    assert runlog.progreso(caso.trace_id).siguiente_paso == "lo resuelve una persona"


def test_el_comprobante_de_otro_cliente_no_pasa_la_validacion(catalogo, raiz):
    """Facturarle al cliente equivocado se atrapa antes del PAC, no después de timbrar."""
    xml = (raiz / "tests" / "fixtures" / "cfdi_valido.xml").read_text(encoding="utf-8")

    dictamen = validar_cfdi(xml, rfc_receptor_esperado=catalogo.cliente("CL-02").rfc)

    assert not dictamen.ok
    assert any(h.regla == "CFDI-030" for h in dictamen.errores)
