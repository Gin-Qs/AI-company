"""svc-budget: tope por agente, alerta al 80% y corte duro."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.budget import (
    PresupuestoExcedido,
    autorizar,
    cargar_politica,
    evaluar,
    exigir,
    panorama,
)
from services.common.errors import ErrorDeValidacion


@pytest.fixture
def politica():
    return cargar_politica()


def test_tope_por_agente_gana_al_nivel(politica):
    """D4-03 tiene tope propio porque cotiza a diario; los demás heredan de su nivel."""
    assert politica.tope("D4-03") == Decimal("2500.00")
    assert politica.tope("D4-03", "Bajo") == Decimal("2500.00")     # el propio manda
    assert politica.tope("D1-01", "Alto") == Decimal("3000.00")
    assert politica.tope("D3-02", "Bajo") == Decimal("600.00")


def test_nivel_desconocido_se_rechaza(politica):
    with pytest.raises(ErrorDeValidacion):
        politica.tope("D9-99", "Altísimo")


def test_costo_estimado_por_nivel(politica):
    """Se estima antes de llamar; el costo real lo registra svc-runlog después."""
    assert politica.costo_estimado(10_000, "Alto") == Decimal("12.00")
    assert politica.costo_estimado(10_000, "Medio") == Decimal("3.50")
    assert politica.costo_estimado(0, "Bajo") == Decimal("0.00")


def test_alerta_al_80_por_ciento(politica):
    justo_antes = evaluar("D4-03", "1999.00", periodo="2026-09", politica=politica)
    en_alerta = evaluar("D4-03", "2000.00", periodo="2026-09", politica=politica)

    assert not justo_antes.en_alerta
    assert en_alerta.en_alerta
    assert en_alerta.consumido_pct == Decimal("80.00")
    assert not en_alerta.excedido
    assert en_alerta.disponible_mxn == Decimal("500.00")


def test_corte_duro_al_llegar_al_tope(politica):
    """§11.5 no contempla pasarse un poquito: al 100% se detiene."""
    decision = autorizar(
        "D4-03", tokens_estimados=1000, consumido="2500.00", periodo="2026-09", politica=politica
    )

    assert not decision.permitida
    assert "agoto su tope" in decision.motivo

    with pytest.raises(PresupuestoExcedido):
        exigir("D4-03", tokens_estimados=1000, consumido="2500.00", periodo="2026-09", politica=politica)


def test_llamada_que_no_cabe_en_lo_disponible(politica):
    decision = autorizar(
        "D3-02", tokens_estimados=10_000_000, consumido="0", periodo="2026-09", nivel="Bajo", politica=politica
    )

    assert not decision.permitida
    assert "quedan" in decision.motivo


def test_llamada_permitida_avisa_si_va_en_alerta(politica):
    decision = autorizar(
        "D4-03", tokens_estimados=2000, consumido="2100.00", periodo="2026-09", politica=politica
    )

    assert decision.permitida
    assert "84.00%" in decision.motivo
    assert exigir("D4-03", tokens_estimados=2000, consumido="0", periodo="2026-09", politica=politica).permitida


def test_consumo_negativo_se_rechaza(politica):
    with pytest.raises(ErrorDeValidacion):
        evaluar("D4-03", "-100", periodo="2026-09", politica=politica)


def test_panorama_ordena_por_presion(politica):
    """El consumo entra tal como lo entrega svc-runlog; los servicios no aparecen: cuestan cero."""
    consumo = {
        "D4-03": {"costo_mxn": Decimal("500.00"), "tokens": 1000, "pasos": 3},
        "D5-03": {"costo_mxn": Decimal("2700.00"), "tokens": 9000, "pasos": 12},
        "svc-pricing": {"costo_mxn": Decimal("0.00"), "tokens": 0, "pasos": 40},
    }

    estados = panorama(consumo, periodo="2026-09", niveles={"D5-03": "Alto"}, politica=politica)

    assert [e.agente for e in estados] == ["D5-03", "D4-03"]
    assert estados[0].en_alerta
    assert estados[0].consumido_pct == Decimal("90.00")
    assert estados[1].consumido_pct == Decimal("20.00")


def test_la_politica_declara_que_no_esta_calibrada(politica):
    """Los topes salen del nivel de modelo, no de consumo observado. Todavía no hay consumo."""
    assert politica.calibrado is False
