"""La bitácora del office es una vista de svc-runlog, no un registro paralelo.

Lo que se prueba aquí es la propiedad que justifica la migración: un encargo de la oficina y
un caso de negocio se responden desde el mismo archivo, con el mismo `trace_id` y la misma
máquina de estados. Si esto se rompe, vuelven a existir dos verdades.
"""

from __future__ import annotations

import json

import pytest

from agents.runtime import convocar
from office import bitacora
from office import encargos as encargos_mod
from services.runlog import RunLog

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import migrar_bitacora  # noqa: E402


def abrir(agente: str = "C-03", **cambios) -> encargos_mod.Encargo:
    base = {
        "titulo": "Máquina de estados del módulo HITL",
        "descripcion": "Módulo: backend. Problema: falta expiración. Restricción: el timeout no aprueba.",
        "entregable_esperado": "Diseño de servicios",
        "convocado_por": "D5-01",
    }
    base.update(cambios)
    return convocar(agente, **base)


def registro() -> RunLog:
    return RunLog(bitacora.ARCHIVO)


def test_la_convocatoria_abre_un_caso_en_svc_runlog(oficina_temporal):
    encargo = abrir()

    caso = registro().caso(encargo.trace_id)

    assert caso.tipo == "encargo"
    assert caso.referencia == encargo.id
    assert caso.estado == "recibido"


def test_el_encargo_y_el_caso_no_pueden_contradecirse(oficina_temporal):
    """Cada estado de la oficina tiene su equivalente en la máquina de estados del caso."""
    encargo = abrir()
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    assert registro().caso(encargo.trace_id).estado == "en_proceso"

    encargos_mod.avanzar(encargo.id, "bloqueado", autor="Bruno", nota="falta el SLA")
    assert registro().caso(encargo.trace_id).estado == "bloqueado"

    encargos_mod.avanzar(encargo.id, "en_curso", autor="Mateo")
    encargos_mod.avanzar(encargo.id, "hecho", autor="Bruno")
    assert registro().caso(encargo.trace_id).estado == "entregado"


def test_cerrar_un_encargo_pasa_por_validacion(oficina_temporal):
    """`hecho` no es una transición, es un camino: en la oficina son dos clics y en el
    registro son los pasos que la arquitectura exige antes de dar algo por entregado."""
    encargo = abrir()
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "hecho", autor="Bruno")

    estados = [
        e["a"]
        for e in (json.loads(l) for l in bitacora.ARCHIVO.read_text(encoding="utf-8").splitlines())
        if e.get("evento") == "transicion"
    ]

    assert estados == ["en_proceso", "esperando_validacion", "entregado"]


def test_un_encargo_hitl_pasa_por_la_bandeja_humana(oficina_temporal):
    """Si el encargo requiere firma, el caso espera a una persona antes de entregarse."""
    encargo = abrir(hitl=True)
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "hecho", autor="Gabriel")

    estados = [
        e["a"]
        for e in (json.loads(l) for l in bitacora.ARCHIVO.read_text(encoding="utf-8").splitlines())
        if e.get("evento") == "transicion"
    ]

    assert "esperando_humano" in estados
    assert registro().caso(encargo.trace_id).criticidad == "alta"   # su SLA se mide en horas


def test_la_oficina_pregunta_el_progreso_sin_interpretar_eventos(oficina_temporal):
    encargo = abrir()
    encargos_mod.avanzar(encargo.id, "en_curso", autor="Bruno")
    encargos_mod.avanzar(encargo.id, "bloqueado", autor="Bruno", nota="espera a Gabriel")

    progreso = bitacora.progreso_de(encargo.trace_id)

    assert progreso.estado == "bloqueado"
    assert progreso.siguiente_paso == "lo resuelve una persona"
    assert progreso.referencia == encargo.id


def test_la_vista_de_oficina_no_muestra_los_pasos_de_negocio(oficina_temporal):
    """Un `llamada_llm` de una cotización no es un evento de oficina y no debe aparecer."""
    encargo = abrir()
    registro().registrar_paso(encargo.trace_id, actor="D4-03", tipo="llamada_llm", tokens=900)

    entradas = bitacora.trace_de(encargo.id)

    assert [e.evento for e in entradas] == ["convocatoria"]
    assert registro().consumo()["D4-03"]["tokens"] == 900


def test_evento_desconocido_se_rechaza_en_el_registro(oficina_temporal):
    with pytest.raises(ValueError):
        bitacora.registrar(evento="chisme", agente="C-01")


def test_la_migracion_conserva_fecha_y_trace(oficina_temporal, tmp_path):
    """Importar el histórico con la fecha de la importación lo convertiría en ruido."""
    historico = tmp_path / "bitacora.jsonl"
    historico.write_text(
        "\n".join(
            json.dumps(fila, ensure_ascii=False)
            for fila in (
                {
                    "ts": "2026-08-18T13:40:30+00:00",
                    "trace_id": "TR-20260818-001",
                    "evento": "convocatoria",
                    "agente": "D5-01",
                    "encargo": "E-001",
                    "detalle": "Requerimientos de la bandeja única de HITL",
                    "autor": "Gabriel",
                },
                {
                    "ts": "2026-08-18T13:40:31+00:00",
                    "trace_id": "TR-20260818-001",
                    "evento": "inicio",
                    "agente": "D5-01",
                    "encargo": "E-001",
                    "detalle": "en redacción",
                    "autor": "Mateo",
                },
            )
        ),
        encoding="utf-8",
    )

    resumen = migrar_bitacora.migrar(historico)
    entradas = bitacora.trace_de("E-001")

    assert resumen == {"leidos": 2, "importados": 2, "omitidos": 0}
    assert [e.ts for e in entradas] == ["2026-08-18T13:40:30+00:00", "2026-08-18T13:40:31+00:00"]
    assert registro().caso("TR-20260818-001").estado == "en_proceso"

    # Idempotente: correrla dos veces no duplica la historia.
    assert migrar_bitacora.migrar(historico) == {"leidos": 2, "importados": 0, "omitidos": 2}
    assert len(bitacora.trace_de("E-001")) == 2
