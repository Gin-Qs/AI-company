"""svc-trace: cada cifra con su origen, y el número inventado que no pasa."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.trace import (
    EntregableNoCuadra,
    Libro,
    exigir_reconciliacion,
    numeros_en_texto,
    reconciliar,
)


@pytest.fixture
def libro() -> Libro:
    libro = Libro(trace_id="TR-20260818-001")
    libro.registrar(
        "precio", "26500.00", servicio="svc-pricing", consulta="tarifa TF-001 vigente al 2026-08-18"
    )
    libro.registrar(
        "margen_pct", "18.30", servicio="svc-profitability", consulta="margen real R-MTY-CDMX", unidad="pct"
    )
    return libro


def entregable(**cambios) -> dict:
    base = {
        "cifras": {"precio": "26500.00", "margen_pct": "18.30"},
        "fuentes": {"precio": "CF-001", "margen_pct": "CF-002"},
        "resumen": "Propuesta por $26,500.00 con un margen de 18.30%.",
    }
    base.update(cambios)
    return base


def test_cifra_se_registra_con_su_origen(libro):
    cifra = libro.cifras["CF-001"]

    assert cifra.nombre == "precio"
    assert cifra.valor == Decimal("26500.00")
    assert cifra.servicio == "svc-pricing"
    assert "TF-001" in cifra.consulta
    assert cifra.trace_id == "TR-20260818-001"
    assert libro.por_nombre("margen_pct").unidad == "pct"


def test_entregable_que_cuadra_pasa(libro):
    resultado = reconciliar(entregable(), libro)

    assert resultado.ok
    assert resultado.verificadas == 2
    assert "2 cifra(s) reconciliadas" in resultado.resumen()


def test_discrepancia_contra_el_origen(libro):
    """Citar 27,000 cuando el origen dice 26,500 no es un redondeo: es otra cifra."""
    resultado = reconciliar(entregable(cifras={"precio": "27000.00"}, fuentes={"precio": "CF-001"}), libro)

    assert not resultado.ok
    discrepancia = resultado.discrepancias[0]
    assert discrepancia.citado == "27000.00"
    assert discrepancia.registrado == "26500.00"
    assert discrepancia.cifra_id == "CF-001"


def test_cifra_sin_fuente_declarada(libro):
    resultado = reconciliar(
        entregable(cifras={"precio": "26500.00", "costo": "21000.00"}, fuentes={"precio": "CF-001"}),
        libro,
        revisar_texto=False,
    )

    assert resultado.sin_fuente == ["costo"]
    assert not resultado.ok


def test_fuente_que_no_existe(libro):
    resultado = reconciliar(
        entregable(cifras={"precio": "26500.00"}, fuentes={"precio": "CF-999"}), libro, revisar_texto=False
    )

    assert resultado.fuente_inexistente == ["precio -> CF-999"]


def test_numero_inventado_en_prosa_se_detecta(libro):
    """El caso real: el margen registrado es 18.30% y el texto dice 22.4% porque suena mejor."""
    inflado = entregable(resumen="Propuesta por $26,500.00 con un margen cercano al 22.4%.")

    resultado = reconciliar(inflado, libro)

    assert not resultado.ok
    assert resultado.numeros_sueltos == ["resumen: 22.4"]
    assert "sin respaldo" in resultado.resumen()


def test_los_numeros_de_uso_comun_no_son_falsos_positivos(libro):
    prosa = entregable(resumen="Son $26,500.00 al 18.30%, con 2 unidades y 3 días de tránsito.")

    assert reconciliar(prosa, libro).ok


def test_numeros_en_texto_normaliza_formatos():
    encontrados = numeros_en_texto("Total $1,234.50 y 22.4% sobre 930 km")

    assert Decimal("1234.50") in encontrados
    assert Decimal("22.4") in encontrados
    assert Decimal("930") in encontrados


def test_reconciliacion_bloquea_el_entregable(libro):
    with pytest.raises(EntregableNoCuadra) as excinfo:
        exigir_reconciliacion(entregable(cifras={"precio": "30000.00"}, fuentes={"precio": "CF-001"}), libro)

    assert excinfo.value.codigo == "TRACE-NO-CUADRA"
    assert exigir_reconciliacion(entregable(), libro).verificadas == 2


def test_cifra_duplicada_se_rechaza(libro):
    from services.common.errors import ErrorDeServicio

    with pytest.raises(ErrorDeServicio):
        libro.registrar("otro", "1", servicio="svc-x", consulta="y", cifra_id="CF-001")
