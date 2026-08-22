"""La línea de comandos de la Fase 3: el brief exactamente como lo narraría D1-03."""

from __future__ import annotations

from services import cli


def test_brief_corre_de_punta_a_punta(capsys, raiz):
    codigo = cli.main(
        ["brief", "--datos", str(raiz / "data" / "ejemplo"), "--corte", "2026-06-30", "--saldo-inicial", "10000"]
    )
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "TESORERIA" in salida
    assert "TABLERO" in salida
    assert "ALERTAS" in salida
    assert "BRIEF (lo que D1-03 narraria)" in salida


def test_brief_solo_narra_lo_que_svc_alerts_selecciono(capsys, raiz):
    """El caso que importa: una alerta calculada pero de severidad menor no llega al brief."""
    codigo = cli.main(
        ["brief", "--datos", str(raiz / "data" / "ejemplo"), "--corte", "2026-06-30", "--saldo-inicial", "10000"]
    )
    salida = capsys.readouterr().out

    assert codigo == 0
    bloque_alertas = salida.split("BRIEF (lo que D1-03 narraria)")[0]
    bloque_brief = salida.split("BRIEF (lo que D1-03 narraria)")[1]

    assert "[BRIEF]" in bloque_alertas          # al menos una alerta entra
    assert "[     ]" in bloque_alertas          # y al menos una se calcula pero no entra
    assert "cartera" not in bloque_brief.lower()  # la de severidad media no aparece narrada


def test_brief_sin_saldo_inicial_declarado_usa_cero(capsys, raiz):
    codigo = cli.main(["brief", "--datos", str(raiz / "data" / "ejemplo"), "--corte", "2026-06-30"])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "saldo inicial declarado: $ 0.00" in salida
