"""La oficina: encargos, bitácora, estado del plano y generación del HTML."""

from __future__ import annotations

import json

import pytest

from agents.runtime import convocar
from office import bitacora, build
from office import encargos as encargos_mod
from office.estado import construir


def abrir(agente: str = "C-03", **cambios) -> encargos_mod.Encargo:
    base = {
        "titulo": "Máquina de estados del módulo HITL",
        "descripcion": "Módulo: backend. Problema: falta el flujo de expiración. Restricción: el timeout no aprueba.",
        "entregable_esperado": "Diseño de servicios",
        "convocado_por": "D5-01",
    }
    base.update(cambios)
    return convocar(agente, **base)


def test_encargo_recorre_los_estados_previstos(oficina_temporal):
    encargo = abrir()
    assert encargo.estado == "pendiente"

    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "bloqueado", autor="Bruno", nota="falta definir el SLA")
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Mateo", nota="SLA definido")
    cerrado = encargos_mod.avanzar(encargo.id, "hecho", autor="Bruno")

    assert cerrado.estado == "hecho"
    assert not cerrado.abierto


def test_transicion_invalida_se_rechaza(oficina_temporal):
    encargo = abrir()

    with pytest.raises(encargos_mod.TransicionInvalida) as excinfo:
        encargos_mod.avanzar(encargo.id, "hecho", autor="Bruno")

    assert "pendiente" in str(excinfo.value)

    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "hecho", autor="Bruno")
    with pytest.raises(encargos_mod.TransicionInvalida):
        encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")


def test_cada_cambio_de_estado_queda_en_la_bitacora(oficina_temporal):
    """R7: si no está en la bitácora, no ocurrió."""
    encargo = abrir()
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "bloqueado", autor="Bruno", nota="espera a Gabriel")
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Gabriel")

    eventos = [e.evento for e in bitacora.trace_de(encargo.id)]

    assert eventos == ["convocatoria", "inicio", "bloqueo", "desbloqueo"]
    assert {e.trace_id for e in bitacora.trace_de(encargo.id)} == {encargo.trace_id}


def test_evento_desconocido_se_rechaza(oficina_temporal):
    with pytest.raises(ValueError):
        bitacora.registrar(evento="chisme", agente="C-01")


def test_estado_traduce_encargos_a_postura(oficina_temporal):
    """Lo que se ve en el plano sale del estado real, no de una animación decorativa."""
    tecleando = abrir("C-03")
    encargos_mod.avanzar(tecleando.id, "en_curso", autor="Bruno")
    bloqueado = abrir("C-06", titulo="Matriz de roles")
    encargos_mod.avanzar(bloqueado.id, "en_curso", autor="Vera")
    encargos_mod.avanzar(bloqueado.id, "bloqueado", autor="Vera", nota="falta decidir quién aprueba")
    abrir("C-09", titulo="Diccionario de datos")

    por_id = {a["id"]: a for a in construir()["agentes"]}

    assert por_id["C-03"]["postura"] == "en_curso"
    assert por_id["C-06"]["postura"] == "bloqueado"     # el bloqueo gana sobre el resto
    assert por_id["C-09"]["postura"] == "pendiente"
    assert por_id["C-01"]["postura"] == "libre"
    assert por_id["D5-02"]["postura"] == "vacante"      # planned: silla vacía


def test_estado_resume_el_avance(oficina_temporal):
    primero = abrir("C-03")
    segundo = abrir("C-07", titulo="Criterios de aceptación")
    encargos_mod.avanzar(primero.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(primero.id, "hecho", autor="Bruno")

    resumen = construir()["resumen"]

    assert resumen["encargos"] == 2
    assert resumen["hechos"] == 1
    assert resumen["abiertos"] == 1
    assert resumen["avance_pct"] == 50
    assert resumen["disponibles"] == 11        # los 9 consultores + D5-01 + D5-03
    assert resumen["listos"] == 4              # D4-03, D2-03, D2-04 y D3-05: sin encender
    assert resumen["agentes"] == 16            # con la silla vacía de D5-02
    assert segundo.estado == "pendiente"


def test_build_incrusta_un_estado_json_valido(oficina_temporal, tmp_path):
    encargo = abrir("C-03")
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")

    destino = build.escribir(tmp_path / "oficina.html")
    html = destino.read_text(encoding="utf-8")

    crudo = html.split("const ESTADO = /*__ESTADO__*/")[1]
    estado, _ = json.JSONDecoder().raw_decode(crudo)

    assert estado["resumen"]["en_curso"] == 1
    assert any(a["nombre"] == "Dalia" for a in estado["agentes"])
    assert "Oficina Fleeter" in html
    assert "getContext" in html


def test_el_plano_dibuja_a_todos_los_que_tienen_identidad(oficina_temporal):
    estado = construir()

    assert len(estado["agentes"]) == 16
    for agente in estado["agentes"]:
        assert agente["escritorio"]["x"] is not None
        assert agente["sprite"], f"{agente['id']} sin sprite"
        assert agente["zona"] in estado["zonas"]


def test_la_pausa_detiene_las_convocatorias(oficina_temporal, monkeypatch):
    """Con la oficina en pausa nadie convoca a nadie, ni Dirección."""
    from agents import runtime
    from office import estado as estado_mod

    pausa = oficina_temporal / "pausa.yaml"
    pausa.write_text(
        "activa: true\ndesde: 2026-08-18\npor: Gabriel\nmotivo: sentar las bases de la Fase 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(estado_mod, "PAUSA", pausa)

    with pytest.raises(runtime.OficinaEnPausa) as excinfo:
        abrir("C-03")

    assert "Gabriel" in str(excinfo.value)


def test_en_pausa_todos_aparecen_pausados_menos_la_silla_vacia(oficina_temporal, monkeypatch):
    """El plano dice lo mismo que el archivo: nadie está tecleando durante una pausa."""
    from office import estado as estado_mod

    encargo = abrir("C-03")
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")

    pausa = oficina_temporal / "pausa.yaml"
    pausa.write_text("activa: true\ndesde: 2026-08-18\npor: Gabriel\n", encoding="utf-8")
    monkeypatch.setattr(estado_mod, "PAUSA", pausa)

    estado = construir()
    por_id = {a["id"]: a for a in estado["agentes"]}

    assert estado["pausa"]["activa"]
    assert por_id["C-03"]["postura"] == "pausado"      # tenía un encargo en curso
    assert por_id["D5-02"]["postura"] == "vacante"     # su fase sigue sin llegar
    assert por_id["C-03"]["encargos"][0]["estado"] == "en_curso"   # el encargo no se pierde
