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


def test_los_dos_agentes_de_la_fase_1_estan_declarados(raiz):
    registro = validate_registry.cargar_registro(raiz)
    fase_1 = {aid for aid, a in registro.agentes.items() if a.get("fase") == 1}

    assert fase_1 == {"D4-03", "D2-03"}
    for agente_id in fase_1:
        assert registro.agentes[agente_id]["estado"] == "listo"


def test_la_regla_de_los_agentes_listos_esta_activa(raiz):
    """Con dos agentes en `listo`, la regla 13 no puede estar omitida."""
    resultados = {r.numero: r for r in validate_registry.validar(raiz)}

    assert resultados["13"].estado == "OK"


def test_un_agente_listo_sin_condiciones_falla(raiz, tmp_path):
    """La regla que impide que `listo` sea un adjetivo sin consecuencias."""
    import shutil

    copia = tmp_path / "repo"
    shutil.copytree(raiz / "registry", copia / "registry")
    (copia / "tests").mkdir()
    suelto = copia / "registry" / "agents" / "D4-03-pricing-y-propuestas.yaml"
    texto = suelto.read_text(encoding="utf-8")
    suelto.write_text(texto[: texto.index("condiciones_encendido:")], encoding="utf-8")

    resultados = {r.numero: r for r in validate_registry.validar(copia)}

    assert any("D4-03 esta listo sin declarar condiciones_encendido" in f for f in resultados["13"].fallas)


# --- Fase 2: construida ------------------------------------------------------


def test_la_fase_2_esta_declarada_completa(raiz):
    registro = validate_registry.cargar_registro(raiz)
    servicios = {sid for sid, s in registro.servicios.items() if s.get("fase") == 2}
    agentes = {aid for aid, a in registro.agentes.items() if a.get("fase") == 2}

    assert servicios == {"svc-doc-checklist", "svc-invoicing", "svc-cfdi-validate", "svc-ar", "svc-notify"}
    assert agentes == {"D3-05", "D2-04"}


def test_los_cinco_servicios_de_la_fase_2_estan_construidos(raiz):
    registro = validate_registry.cargar_registro(raiz)

    for servicio_id, servicio in registro.servicios.items():
        if servicio.get("fase") != 2:
            continue
        assert servicio["estado"] == "built", servicio_id
        assert (raiz / servicio["modulo"]).is_dir(), servicio_id


def test_los_dos_agentes_de_la_fase_2_estan_listos_sin_encender(raiz):
    """Los servicios existen; la bandeja de HITL y los datos fiscales, no."""
    registro = validate_registry.cargar_registro(raiz)

    for agente_id in ("D3-05", "D2-04"):
        agente = registro.agentes[agente_id]
        assert agente["estado"] == "listo"
        pendientes = [c for c in agente["condiciones_encendido"] if not c.get("cumplida")]
        assert pendientes, f"{agente_id} sin nada pendiente y sin encender"


def test_cada_servicio_de_la_fase_2_declara_sus_limites_y_lo_que_falta_decidir(raiz):
    """Construirlo no cierra las decisiones: los catálogos siguen sin confirmar."""
    registro = validate_registry.cargar_registro(raiz)

    for servicio_id, servicio in registro.servicios.items():
        if servicio.get("fase") != 2:
            continue
        assert servicio.get("tests"), f"{servicio_id} sin pruebas declaradas"
        assert servicio.get("decisiones_pendientes"), f"{servicio_id} sin decisiones pendientes"
        assert servicio.get("limits"), f"{servicio_id} sin límites"


def test_el_validador_de_cfdi_declara_que_no_sustituye_al_xsd(raiz):
    """El límite más importante del servicio vive en su contrato, no sólo en el código."""
    registro = validate_registry.cargar_registro(raiz)

    assert registro.servicios["svc-cfdi-validate"]["valida_xsd"] is False


def test_un_servicio_planned_puede_declarar_pruebas_que_aun_no_existen(raiz, tmp_path):
    """La regla que permite preparar una fase: pendiente en planned, falla en built."""
    import shutil

    copia = tmp_path / "repo"
    shutil.copytree(raiz / "registry", copia / "registry")
    shutil.copytree(raiz / "tests", copia / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    suelto = copia / "registry" / "services" / "svc-kpi.yaml"
    suelto.write_text(
        "id: svc-kpi\nname: KPI\ntype: deterministic_python\nestado: planned\nfase: 3\n"
        "consumidores: [D1-03]\ntests:\n  - test_que_nadie_ha_escrito_todavia\n",
        encoding="utf-8",
    )

    resultados = {r.numero: r for r in validate_registry.validar(copia)}

    assert resultados["7b"].estado == "OK"
    assert any("test_que_nadie_ha_escrito_todavia" in p for p in resultados["7b"].pendientes)

    suelto.write_text(suelto.read_text(encoding="utf-8").replace("estado: planned", "estado: built"), encoding="utf-8")
    resultados = {r.numero: r for r in validate_registry.validar(copia)}

    assert resultados["7b"].fallas      # el mismo test declarado, ahora en built, reprueba


def test_el_agente_de_facturacion_no_puede_timbrar_solo(raiz):
    """§11.4, regla dura: toda ACT-DOC-S es HITL siempre, y se verifica en el registro."""
    registro = validate_registry.cargar_registro(raiz)
    d2_04 = registro.agentes["D2-04"]

    assert "ACT-DOC-S" in d2_04["actions"]
    assert "CTL-HITL" in d2_04["controls"]
    assert "no_emite_cfdi_sin_hitl" in d2_04["limits"]
