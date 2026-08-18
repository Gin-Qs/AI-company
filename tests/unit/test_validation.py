"""svc-validation: el contrato de entregable de §7.1 y las reglas de dominio."""

from __future__ import annotations

import pytest

from services.validation import CAMPOS_ENTREGABLE, EntregableRechazado, exigir, validar


def entregable(**cambios) -> dict:
    base = {
        "decision_solicitada": "autorizar la cotización de CL-01",
        "fuentes": {"precio": "CF-001", "margen_pct": "CF-002"},
        "supuestos": ["diesel al precio ponderado de agosto"],
        "confianza": {"nivel": "media", "limitado_por": "un solo trimestre de histórico"},
        "opciones": ["tarifa de tabla", "tarifa con 3% de descuento"],
        "si_no_respondes": "la cotización no sale y el cliente decide con otro; 2 días hábiles",
        "cifras": {"precio": "26500.00", "margen_pct": "18.30"},
    }
    base.update(cambios)
    return base


def test_entregable_completo_pasa():
    dictamen = validar(entregable(), "entregable")

    assert dictamen.ok
    assert dictamen.hallazgos == []


@pytest.mark.parametrize("campo", CAMPOS_ENTREGABLE)
def test_entregable_sin_los_seis_campos_se_rechaza(campo):
    """§7.1: falta uno de los seis, se rechaza. Sin excepciones por campo."""
    incompleto = entregable()
    del incompleto[campo]

    dictamen = validar(incompleto, "entregable")

    assert not dictamen.ok
    assert any(h.campo == campo and h.regla == "VAL-ENT-001" for h in dictamen.errores)


def test_decision_con_una_sola_opcion_se_rechaza():
    """Una recomendación única disfrazada de conclusión es exactamente lo que §7.1 prohíbe."""
    dictamen = validar(entregable(opciones=["subir el precio"]), "entregable")

    assert not dictamen.ok
    assert any(h.regla == "VAL-ENT-002" for h in dictamen.errores)

    # Con la justificación explícita sí pasa: a veces de verdad hay un solo camino.
    justificado = entregable(opciones=["subir el precio"], opcion_unica_justificada="la tabla no admite descuento")
    assert validar(justificado, "entregable").ok


def test_informativo_no_necesita_opciones():
    informativo = entregable(decision_solicitada="ninguna, es informativo", opciones=["-"])

    assert validar(informativo, "entregable").ok


def test_confianza_declara_que_la_limita():
    solo_nivel = validar(entregable(confianza="media"), "entregable")
    sin_limite = validar(entregable(confianza={"nivel": "media"}), "entregable")
    nivel_raro = validar(entregable(confianza={"nivel": "altísima", "limitado_por": "nada"}), "entregable")

    assert any(h.regla == "VAL-ENT-003" for h in solo_nivel.errores)
    assert any(h.campo == "confianza.limitado_por" for h in sin_limite.errores)
    assert any(h.campo == "confianza.nivel" for h in nivel_raro.errores)


def test_cifra_sin_fuente_se_detecta():
    sin_fuente = entregable(cifras={"precio": "26500.00", "margen_pct": "18.30", "costo": "21000.00"})

    dictamen = validar(sin_fuente, "entregable")

    assert [h.campo for h in dictamen.errores] == ["fuentes.costo"]


def test_plazo_sin_tiempo_es_advertencia_no_error():
    """Que no diga el plazo es un defecto, pero no motivo para tirar el entregable."""
    dictamen = validar(entregable(si_no_respondes="se pierde la venta"), "entregable")

    assert dictamen.ok
    assert [h.regla for h in dictamen.advertencias] == ["VAL-ENT-005"]


def test_cotizacion_bajo_el_minimo_es_error():
    dictamen = validar(
        {"margen_pct": "12.00", "margen_minimo_pct": "18.00", "precio_mxn": "24000", "costo_mxn": "21120"},
        "cotizacion",
    )

    assert not dictamen.ok
    assert any(h.regla == "VAL-COT-001" for h in dictamen.errores)


def test_descuento_sobre_el_umbral_es_error():
    dictamen = validar(
        {
            "margen_pct": "19.00",
            "margen_minimo_pct": "18.00",
            "descuento_pct": "8.00",
            "descuento_max_pct": "5.00",
            "precio_mxn": "26000",
            "costo_mxn": "21060",
        },
        "cotizacion",
    )

    assert any(h.regla == "VAL-COT-002" for h in dictamen.errores)


def test_precio_que_no_cubre_el_costo():
    dictamen = validar(
        {"margen_pct": "18.00", "margen_minimo_pct": "18.00", "precio_mxn": "20000", "costo_mxn": "21000"},
        "cotizacion",
    )

    assert any(h.regla == "VAL-COT-003" for h in dictamen.errores)


def test_costeo_incoherente_se_detecta():
    dictamen = validar(
        {
            "desglose": {"diesel": "10000.00", "casetas": "2000.00"},
            "variable_cost": "20000.00",     # no cuadra con el desglose
            "fixed_allocated_cost": "1000.00",
            "total_trip_cost": "21000.00",
            "cost_per_km": "21.0000",
            "assumptions": [],
        },
        "costeo",
    )

    assert any("desglose" in h.campo for h in dictamen.errores)


def test_costeo_sin_supuestos_se_detecta():
    dictamen = validar({"cost_per_km": "21.0000"}, "costeo")

    assert any(h.regla == "VAL-CST-002" for h in dictamen.errores)


def test_exigir_levanta_con_el_detalle():
    with pytest.raises(EntregableRechazado) as excinfo:
        exigir(entregable(supuestos=[], confianza=""), "entregable")

    error = excinfo.value
    assert error.codigo == "VAL-RECHAZADO"
    assert len(error.contexto["hallazgos"]) >= 2
    assert exigir(entregable(), "entregable").ok


def test_ambito_desconocido_se_rechaza():
    from services.common.errors import ErrorDeServicio

    with pytest.raises(ErrorDeServicio):
        validar({}, "poesia")
