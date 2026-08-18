"""El registro cumple la seccion 10.3. Requisito de arranque de la Fase 1."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import validate_registry  # noqa: E402


def test_registro_sin_fallas(raiz):
    resultados = validate_registry.validar(raiz)
    fallas = {r.numero: r.fallas for r in resultados if r.fallas}

    assert fallas == {}


def test_reglas_omitidas_declaran_motivo(raiz):
    """Una regla omitida no es una regla en verde: tiene que decir por que se omitio."""
    for resultado in validate_registry.validar(raiz):
        if resultado.estado == "OMITIDA":
            assert resultado.omitida


def test_los_cuatro_servicios_de_la_fase_0_estan_registrados(raiz):
    registro = validate_registry.cargar_registro(raiz)
    fase_0 = {sid for sid, s in registro.servicios.items() if s.get("fase") == 0}

    assert fase_0 == {"svc-masterdata", "svc-ingest", "svc-costing", "svc-profitability"}
    for servicio_id in fase_0:
        assert registro.servicios[servicio_id]["estado"] == "built"


def test_ningun_servicio_de_la_fase_0_declara_acciones(raiz):
    """La Fase 0 no ejecuta ningun ACT-*: es su condicion de arranque (seccion 17.5)."""
    registro = validate_registry.cargar_registro(raiz)

    for servicio in registro.servicios.values():
        assert not servicio.get("actions")
        assert not servicio.get("acciones_act")


def test_main_devuelve_cero(raiz, capsys):
    codigo = validate_registry.main(["--raiz", str(raiz), "--verbose"])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "FALLA" not in salida


@pytest.mark.parametrize("regla", ["5", "6", "7", "7b", "7c", "10"])
def test_reglas_aplicables_hoy_no_estan_omitidas(raiz, regla):
    """Estas reglas no dependen de agentes: si se omiten, el validador se rompio."""
    resultados = {r.numero: r for r in validate_registry.validar(raiz)}

    assert resultados[regla].estado == "OK"
