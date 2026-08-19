"""La línea de comandos de la Fase 2, y la cartera armada desde lo que ya normalizó la Fase 0.

Los códigos de salida son parte del contrato: `facturar` sale con 1 porque el comprobante
siempre queda esperando una firma, y con 3 cuando la puerta documental no lo deja pasar.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services import cli
from services.ar import cartera_desde_operacion


@pytest.fixture(autouse=True)
def folios_temporales(tmp_path, monkeypatch):
    """El libro de folios es append-only: una prueba no escribe en el de la empresa."""
    from services.invoicing import comprobante

    monkeypatch.setattr(comprobante, "LIBRO_POR_DEFECTO", tmp_path / "folios.jsonl")
    return tmp_path


def test_facturar_arma_el_borrador_y_espera_firma(capsys, raiz):
    codigo = cli.main(
        [
            "facturar",
            "--datos", str(raiz / "data" / "ejemplo"),
            "--viaje", "T-1001",
            "--cliente", "CL-01",
            "--flete", "26500",
            "--documentos", "orden_de_servicio,carta_porte,pod",
            "--fecha", "2026-06-01",
        ]
    )
    salida = capsys.readouterr().out

    assert codigo == 1                      # nunca 0: falta la firma humana
    assert "COMPLETO" in salida
    assert "29680.00" in salida
    assert "ACT-DOC-S es CTL-HITL siempre" in salida


def test_facturar_sin_expediente_no_produce_borrador(capsys, raiz):
    codigo = cli.main(
        [
            "facturar",
            "--datos", str(raiz / "data" / "ejemplo"),
            "--viaje", "T-1001",
            "--cliente", "CL-01",
            "--flete", "26500",
            "--documentos", "orden_de_servicio",
            "--fecha", "2026-06-01",
        ]
    )
    capturado = capsys.readouterr()

    assert codigo == 3
    assert "NO SE FACTURA" in capturado.err
    assert "BORRADOR" not in capturado.out


def test_cartera_desde_la_operacion_declara_sus_supuestos(raiz):
    """Deducir la factura del ingreso del viaje es una aproximación, y se dice."""
    resultado = cartera_desde_operacion(raiz / "data" / "ejemplo", corte=date(2026, 6, 30))

    assert len(resultado.facturas) == 12
    assert resultado.cartera.saldo_total_mxn == Decimal("219600.00")
    assert resultado.cartera.sin_identificar_mxn > 0        # el banco no trae la factura
    assert len(resultado.supuestos) == 2
    assert "supuestos" in resultado.as_dict()


def test_cartera_por_linea_de_comandos(capsys, raiz):
    codigo = cli.main(["cartera", "--datos", str(raiz / "data" / "ejemplo"), "--corte", "2026-06-30"])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "PRIORIDAD DE COBRANZA" in salida
    assert "sin calibrar" in salida          # la rúbrica todavía no lo está, y se ve
