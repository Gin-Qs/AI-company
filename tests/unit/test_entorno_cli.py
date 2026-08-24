"""El guardarrail de §4: el CLI no escribe estado operativo fuera de desarrollo.

Despues del portal, Postgres es la verdad operativa. Pero `office.cli convocar` sigue sabiendo
escribir un YAML en `office/encargos/` y un evento en el JSONL. Correrlo contra el sistema en
produccion crea un encargo que el portal no ve — y a partir de ahi "¿cuantos encargos hay
abiertos?" tiene dos respuestas.

Hoy los doce YAML y las doce filas de Postgres coinciden **solo porque nadie ha creado uno
nuevo desde ninguno de los dos lados**. Estas pruebas fijan que no se pueda.
"""

from __future__ import annotations

import pytest

from office import cli, entorno


@pytest.fixture(autouse=True)
def sin_declarar(monkeypatch):
    monkeypatch.delenv(entorno.VARIABLE, raising=False)


# --- la decision -------------------------------------------------------------


def test_sin_la_variable_no_es_local():
    assert entorno.es_local() is False
    with pytest.raises(entorno.EscrituraFueraDeLocal):
        entorno.exigir_local("convocar")


def test_con_la_variable_deja_pasar(monkeypatch):
    monkeypatch.setenv(entorno.VARIABLE, "local")
    assert entorno.es_local() is True
    entorno.exigir_local("convocar")  # no levanta


def test_no_distingue_mayusculas_ni_espacios(monkeypatch):
    """Un `LOCAL ` con espacio detras es la misma intencion. Fallar ahi solo ensena a pelearse
    con la herramienta."""
    for valor in ("local", "LOCAL", " Local "):
        monkeypatch.setenv(entorno.VARIABLE, valor)
        assert entorno.es_local() is True, valor


@pytest.mark.parametrize("valor", ["", "produccion", "prod", "1", "true", "si"])
def test_cualquier_otro_valor_no_abre_la_puerta(monkeypatch, valor):
    """Se exige la palabra, no un booleano. `AI_COMPANY_ENTORNO=true` no declara nada."""
    monkeypatch.setenv(entorno.VARIABLE, valor)
    assert entorno.es_local() is False


def test_el_mensaje_manda_al_portal_y_dice_como_desarrollar():
    """Un error que solo dice «no permitido» manda a buscar como saltarselo, y saltarselo es
    justo lo que crea la segunda verdad."""
    with pytest.raises(entorno.EscrituraFueraDeLocal) as fallo:
        entorno.exigir_local("avanzar")
    texto = str(fallo.value)
    assert "avanzar" in texto
    assert "portal" in texto.lower()
    assert entorno.VARIABLE in texto


# --- los comandos ------------------------------------------------------------


ESCRITURA = [
    ["convocar", "C-04", "--titulo", "t", "--descripcion", "d", "--entregable", "e", "--por", "Gabriel"],
    ["avanzar", "E-002", "en_curso", "--autor", "Dalia"],
    ["recordar", "C-04", "una nota", "--tipo", "decision"],
]


@pytest.mark.parametrize("argv", ESCRITURA, ids=lambda a: a[0])
def test_los_comandos_de_escritura_se_rechazan(argv, capsys):
    assert cli.main(argv) == 2
    assert "RECHAZADO" in capsys.readouterr().err


@pytest.mark.parametrize("argv", ESCRITURA, ids=lambda a: a[0])
def test_y_no_escriben_nada_antes_de_rechazar(argv, tmp_path, monkeypatch):
    """El guardarrail va ANTES de tocar disco. Si corriera despues, el encargo quedaria
    escrito y el rechazo seria decorativo."""
    from office import encargos as encargos_mod

    monkeypatch.setattr(encargos_mod, "DIRECTORIO", tmp_path)
    cli.main(argv)
    assert list(tmp_path.iterdir()) == []


def test_estado_no_necesita_declarar_nada(capsys):
    """Leer siempre se puede. Si `estado` tambien exigiera la variable, nadie podria mirar la
    oficina desde ningun sitio."""
    assert cli.main(["estado"]) == 0
    assert capsys.readouterr().out.strip()


def test_los_comandos_de_lectura_no_pasan_por_el_guardarrail(monkeypatch):
    """Se comprueba desde el otro lado: si alguien agregara `exigir_local` a `estado`, esto
    se pondria rojo."""
    llamadas = []
    monkeypatch.setattr(entorno, "exigir_local", lambda c: llamadas.append(c))
    monkeypatch.setattr(cli, "exigir_local", lambda c: llamadas.append(c))
    cli.main(["estado"])
    assert llamadas == []
