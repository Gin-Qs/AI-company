"""La fila que la CI escribe en `validacion_registro` (docs/portal.md §11).

Lo que se prueba no es que Postgres acepte el insert —eso lo dira el dia que exista el
secreto— sino la traduccion: que la fila lleve todo lo que la columna exige, y que "en verde"
signifique lo que dice.
"""

from __future__ import annotations

import json

from scripts.publicar_validacion import SQL, fila, resumen_de_pytest

RESULTADO = {
    "commit_sha": "abc1234def",
    "rama": "main",
    "reglas": [
        {"numero": "1", "descripcion": "x", "estado": "OK", "fallas": [], "pendientes": [], "omitida": ""},
        {"numero": "2", "descripcion": "y", "estado": "OMITIDA", "fallas": [], "pendientes": [], "omitida": "falta insumo"},
    ],
    "total_reglas": 2,
    "en_verde": 1,
    "en_falla": 0,
    "omitidas": 1,
    "pendientes": 0,
}


def test_la_fila_tiene_tantos_valores_como_columnas():
    """`total_reglas` es not null sin default. Olvidarlo revienta la insercion en produccion
    y en ningun otro lado: aqui se cuenta antes."""
    columnas = SQL.split("(", 1)[1].split(")")[0].count(",") + 1
    assert len(fila(RESULTADO, pytest_ok=True, pytest_total=290)) == columnas


def test_las_reglas_viajan_como_json_valido():
    reglas = json.loads(fila(RESULTADO, pytest_ok=True, pytest_total=1)[2])
    assert [r["numero"] for r in reglas] == ["1", "2"]


def test_el_total_no_se_recalcula_sumando_las_otras_cifras():
    """Una regla que no cayera en ninguna categoria es informacion, no un descuadre que
    haya que tapar sumando."""
    raro = {**RESULTADO, "total_reglas": 17, "en_verde": 14, "en_falla": 0, "omitidas": 2}
    assert fila(raro, pytest_ok=True, pytest_total=1)[3] == 17


def test_sin_junit_xml_no_se_declara_en_verde(tmp_path):
    """Si la suite ni arranco, nadie demostro que el codigo funcione."""
    assert resumen_de_pytest(tmp_path / "no-existe.xml") == (False, None)


def test_cero_pruebas_no_es_todo_en_verde(tmp_path):
    xml = tmp_path / "pytest.xml"
    xml.write_text('<testsuites><testsuite tests="0" failures="0" errors="0"/></testsuites>', encoding="utf-8")
    paso, total = resumen_de_pytest(xml)
    assert paso is False
    assert total == 0


def test_una_suite_verde_se_lee_verde_y_con_su_conteo(tmp_path):
    xml = tmp_path / "pytest.xml"
    xml.write_text('<testsuites><testsuite tests="290" failures="0" errors="0"/></testsuites>', encoding="utf-8")
    assert resumen_de_pytest(xml) == (True, 290)


def test_un_error_cuenta_igual_que_una_falla(tmp_path):
    """Una prueba que revienta al importar no aparece en `failures`. Ignorar `errors` haria
    que la vista pintara verde sobre una suite que no corrio."""
    xml = tmp_path / "pytest.xml"
    xml.write_text('<testsuites><testsuite tests="10" failures="0" errors="1"/></testsuites>', encoding="utf-8")
    assert resumen_de_pytest(xml)[0] is False
