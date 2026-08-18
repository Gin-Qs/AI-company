"""El flujo completo de la Fase 1: cotizar sin perder margen.

Los cinco servicios trabajando juntos sobre el catálogo real de `data/ejemplo`, sin agente y
sin LLM. Cuando `D4-03` se encienda, esto es exactamente lo que va a orquestar — y lo único
que el modelo añadirá es la redacción de la propuesta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.budget import autorizar
from services.masterdata import cargar_catalogo
from services.pricing import (
    AGENTE,
    Autorizacion,
    CotizacionBloqueada,
    EntradaCotizacion,
    cotizar,
    dictaminar,
)
from services.runlog import RunLog, entregar
from services.trace import Libro, exigir_reconciliacion
from services.validation import exigir

FECHA = date(2026, 8, 18)
PERIODO = "2026-08"


@pytest.fixture
def catalogo_real(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


@pytest.fixture
def runlog(tmp_path) -> RunLog:
    return RunLog(tmp_path / "runlog.jsonl")


def entregable_de(cotizacion) -> dict:
    """El entregable que el agente redactaría, con el contrato de §7.1 puesto."""
    return {
        "decision_solicitada": f"autorizar la cotización de {cotizacion.cliente_id} para {cotizacion.route_id}",
        "fuentes": cotizacion.fuentes,
        "cifras": cotizacion.cifras,
        "supuestos": [s.detalle for s in cotizacion.assumptions],
        "confianza": {
            "nivel": "media",
            "limitado_por": "el costo por km sale de un trimestre de histórico, no de un año",
        },
        "opciones": ["tarifa de tabla sin descuento", "tarifa con descuento operativo de 4%"],
        "si_no_respondes": "la cotización no sale y el cliente decide con otro transportista; 1 día hábil",
        "resumen": (
            f"Propuesta por ${cotizacion.precio_mxn} con margen de {cotizacion.margen_pct}% "
            f"sobre un costo de ${cotizacion.costo_mxn}."
        ),
    }


def test_flujo_cotizacion_fase1(catalogo_real, runlog):
    """De la solicitud a la entrega, con todo registrado y toda cifra reconciliada."""
    # 1. O1 abre el caso: todo paso posterior hereda el trace.
    caso = runlog.abrir_caso(tipo="cotizacion", referencia="CL-01/R-MTY-CDMX", criticidad="media", actor="O1")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    # 2. Antes de gastar modelo, se pregunta al presupuesto.
    permiso = autorizar("D4-03", tokens_estimados=3000, consumido="0", periodo=PERIODO)
    assert permiso.permitida

    # 3. El precio lo calcula el servicio, no el agente.
    libro = Libro(trace_id=caso.trace_id)
    cotizacion = cotizar(
        EntradaCotizacion(
            route_id="R-MTY-CDMX",
            unit_id="U-101",
            cliente_id="CL-01",
            operador_id="OP-01",
            fecha=FECHA,
            fuel_price=Decimal("26.59"),
        ),
        catalogo_real,
        libro=libro,
    )
    runlog.registrar_paso(
        caso.trace_id,
        actor="svc-pricing",
        tipo="llamada_servicio",
        salidas={"precio": str(cotizacion.precio_mxn), "margen_pct": str(cotizacion.margen_pct)},
        versiones={"servicio_version": "v1.0.0"},
    )
    assert cotizacion.nivel_autorizacion == AGENTE
    assert cotizacion.margen_pct >= cotizacion.margen_minimo_pct

    # 4. El agente redacta; el costo del modelo queda registrado.
    runlog.registrar_paso(
        caso.trace_id, actor="D4-03", tipo="llamada_llm", tokens=2800, costo_mxn="0.98",
        versiones={"prompt_version": "v1.0.0"},
    )
    entregable = entregable_de(cotizacion)

    # 5. Las dos puertas: reglas y reconciliación de cifras.
    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    assert dictaminar(cotizacion).ok
    assert exigir(entregable, "entregable").ok
    assert exigir_reconciliacion(entregable, libro).verificadas == len(cotizacion.cifras)

    # 6. Entrega. Como el gate lo deja en manos del agente, no hay HITL que esperar.
    final = entregar(runlog, caso.trace_id, actor="D4-03")

    assert final.estado == "entregado"
    assert runlog.consumo(periodo=PERIODO)["D4-03"]["costo_mxn"] == Decimal("0.98")
    assert runlog.progreso(caso.trace_id).siguiente_paso == "nada, el caso cerro"


def test_flujo_con_hitl_cuando_el_gate_lo_pide(catalogo_real, runlog):
    """Un descuento negociado no lo cierra el agente: espera a Ana, con SLA corriendo."""
    caso = runlog.abrir_caso(tipo="cotizacion", referencia="CL-02/R-CDMX-GDL", criticidad="media", actor="O1")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    cotizacion = cotizar(
        EntradaCotizacion(
            route_id="R-CDMX-GDL",
            unit_id="U-103",
            cliente_id="CL-02",
            operador_id="OP-03",
            fecha=FECHA,
            fuel_price=Decimal("26.59"),
            descuento_pct=Decimal("4"),
        ),
        catalogo_real,
    )

    assert cotizacion.requiere_humano
    assert cotizacion.quien_autoriza == "Ana"

    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    runlog.transicionar(
        caso.trace_id, "esperando_humano", actor="Ana", motivo=cotizacion.motivo_gate
    )
    progreso = runlog.progreso(caso.trace_id)

    assert progreso.estado == "esperando_humano"
    assert progreso.vence_en is not None
    assert entregar(runlog, caso.trace_id, actor="Ana").estado == "entregado"


def test_bajo_el_minimo_el_caso_se_bloquea_no_se_cotiza(catalogo_real, runlog):
    """El camino que importa: el gate no deja pasar y el caso queda esperando a Dirección."""
    caso = runlog.abrir_caso(tipo="cotizacion", referencia="CL-03/R-MTY-CDMX", criticidad="alta", actor="O1")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    peticion = EntradaCotizacion(
        route_id="R-MTY-CDMX",
        unit_id="U-102",
        cliente_id="CL-03",
        operador_id="OP-01",
        fecha=FECHA,
        fuel_price=Decimal("26.59"),
        descuento_pct=Decimal("15"),
    )

    with pytest.raises(CotizacionBloqueada) as excinfo:
        cotizar(peticion, catalogo_real)

    runlog.registrar_paso(
        caso.trace_id,
        actor="svc-pricing",
        tipo="gate",
        resultado="bloqueado",
        gate={"umbral": "margen_minimo_pct", "requiere": excinfo.value.contexto["requiere"]},
    )
    bloqueado = runlog.transicionar(
        caso.trace_id, "bloqueado", actor="svc-pricing", motivo="margen bajo el mínimo de la ruta"
    )

    assert bloqueado.estado == "bloqueado"
    assert runlog.pasos(caso.trace_id)[-1].gate["requiere"] == "Gabriel"

    # Con autorización de Dirección sí sale, y la excepción queda escrita en la cotización.
    con_permiso = cotizar(
        peticion,
        catalogo_real,
        autorizacion=Autorizacion(quien="Gabriel", motivo="retorno vacío desde CDMX", otorgada="2026-08-18"),
    )
    assert con_permiso.autorizacion.quien == "Gabriel"
    assert con_permiso.margen_pct < con_permiso.margen_minimo_pct


def test_el_entregable_con_una_cifra_inventada_no_pasa(catalogo_real, runlog):
    """La red de seguridad que hace segura la Fase 1: el número que suena mejor no llega al cliente."""
    from services.trace import EntregableNoCuadra

    libro = Libro(trace_id="TR-FASE1")
    cotizacion = cotizar(
        EntradaCotizacion(
            route_id="R-MTY-CDMX",
            unit_id="U-101",
            cliente_id="CL-01",
            operador_id="OP-01",
            fecha=FECHA,
            fuel_price=Decimal("26.59"),
        ),
        catalogo_real,
        libro=libro,
    )
    entregable = entregable_de(cotizacion)
    entregable["resumen"] = "Propuesta con un margen cercano al 34.7%, muy por arriba de la ruta."

    with pytest.raises(EntregableNoCuadra):
        exigir_reconciliacion(entregable, libro)
