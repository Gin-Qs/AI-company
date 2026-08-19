"""svc-notify: plantilla fija, variables validadas y ningún LLM en el camino.

Estas pruebas sostienen una regla del Gate (§11.4): un aviso a cliente **no** es HITL
precisamente porque el texto ya lo aprobó una persona y el sistema sólo rellena huecos que
valida. Si alguna de estas cae, esa excepción deja de estar justificada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.masterdata import cargar_catalogo
from services.notify import (
    DestinatarioDesconocido,
    PlantillaDesconocida,
    VariableInvalida,
    cargar_plantillas,
    enviar,
    render,
)
from services.runlog import RunLog


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


@pytest.fixture
def plantillas():
    return cargar_plantillas()


def variables_de_pago() -> dict:
    return {
        "nombre": "Aceros del Norte",
        "factura_id": "A-1",
        "saldo_mxn": Decimal("29680.00"),
        "vencimiento": date(2026, 7, 1),
    }


def test_plantilla_fija_no_pasa_por_llm(catalogo, plantillas):
    mensaje = render(
        "recordatorio_de_pago", variables_de_pago(), destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas
    )

    assert mensaje.paso_por_llm is False
    assert mensaje.texto == (
        "Buen día Aceros del Norte. Le recordamos la factura A-1 por $29680.00, "
        "con vencimiento el 2026-07-01. Quedamos atentos."
    )
    assert mensaje.plantillas_version == plantillas.version


def test_variable_faltante_no_se_envia(catalogo, plantillas):
    variables = variables_de_pago()
    del variables["vencimiento"]

    with pytest.raises(VariableInvalida) as excinfo:
        render("recordatorio_de_pago", variables, destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas)

    assert "vencimiento" in str(excinfo.value)


def test_variable_con_tipo_invalido_se_rechaza(catalogo, plantillas):
    """Un importe que no es importe llegaría al cliente como texto raro en un cobro."""
    variables = variables_de_pago()
    variables["saldo_mxn"] = "mucho"

    with pytest.raises(VariableInvalida):
        render("recordatorio_de_pago", variables, destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas)

    variables = variables_de_pago()
    variables["vencimiento"] = "el jueves"

    with pytest.raises(VariableInvalida):
        render("recordatorio_de_pago", variables, destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas)


def test_una_variable_de_mas_tambien_se_rechaza(catalogo, plantillas):
    """Suele ser un error de nombre en una que sí hacía falta."""
    variables = variables_de_pago() | {"saldo": Decimal("100")}

    with pytest.raises(VariableInvalida):
        render("recordatorio_de_pago", variables, destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas)


def test_plantilla_desconocida_se_rechaza(catalogo, plantillas):
    with pytest.raises(PlantillaDesconocida):
        render("mensaje_improvisado", {}, destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas)


def test_no_se_manda_a_un_destinatario_fuera_del_maestro(catalogo, plantillas):
    with pytest.raises(DestinatarioDesconocido):
        render(
            "recordatorio_de_pago",
            variables_de_pago(),
            destinatario_id="CL-99",
            catalogo=catalogo,
            plantillas=plantillas,
        )


def test_envio_queda_en_svc_runlog(catalogo, plantillas, tmp_path):
    runlog = RunLog(tmp_path / "runlog.jsonl")
    caso = runlog.abrir_caso(tipo="cobranza", referencia="A-1", actor="D2-04")
    mensaje = render(
        "recordatorio_de_pago", variables_de_pago(), destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas
    )

    envio = enviar(mensaje, runlog=runlog, trace_id=caso.trace_id, plantillas=plantillas)
    pasos = runlog.pasos(caso.trace_id)

    assert pasos[-1].actor == "svc-notify"
    assert pasos[-1].salidas["estado"] == envio.estado
    assert pasos[-1].versiones["plantillas_version"] == plantillas.version


def test_sin_canal_externo_no_dice_enviado(catalogo, plantillas):
    """Decir 'enviado' sin haber enviado es la clase de mentira que nadie detecta después."""
    mensaje = render(
        "documento_faltante",
        {"nombre": "Juan", "trip_id": "T-1001", "documento": "POD firmado"},
        destinatario_id="OP-01",
        catalogo=catalogo,
        plantillas=plantillas,
    )

    envio = enviar(mensaje, plantillas=plantillas)

    assert mensaje.canal == "bitacora"
    assert envio.estado == "registrado_para_envio_humano"


def test_una_plantilla_con_un_hueco_sin_declarar_no_carga(tmp_path):
    """Se detecta al cargar el catálogo, no al intentar mandarle algo a un cliente."""
    roto = tmp_path / "plantillas.yaml"
    roto.write_text(
        "version: v0\naprobadas: true\ncanales: {bitacora: {activo: true}}\n"
        "plantillas:\n  saludo:\n    canal: bitacora\n    asunto: Hola {nombre}\n"
        "    texto: Hola {nombre}, su viaje {trip_id} va en camino\n"
        "    variables:\n      nombre: {tipo: texto}\n",
        encoding="utf-8",
    )

    with pytest.raises(VariableInvalida) as excinfo:
        cargar_plantillas(roto)

    assert "trip_id" in str(excinfo.value)


def test_las_plantillas_declaran_si_estan_aprobadas(plantillas, catalogo):
    mensaje = render(
        "recordatorio_de_pago", variables_de_pago(), destinatario_id="CL-01", catalogo=catalogo, plantillas=plantillas
    )

    assert plantillas.aprobadas is False
    assert mensaje.aprobada is False
