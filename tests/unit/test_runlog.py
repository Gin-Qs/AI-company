"""svc-runlog: máquina de estados, reintentos, progreso, consumo y la regla dura de timeout."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.common.errors import ErrorDeIntegridad
from services.runlog import (
    MAX_REINTENTOS,
    ReintentosAgotados,
    RunLog,
    TransicionInvalida,
    entregar,
    es_habil,
    resolver_vencimiento,
    sumar_horas_habiles,
)
from services.runlog.sla import HUSO, ACCIONES


@pytest.fixture
def runlog(tmp_path) -> RunLog:
    return RunLog(tmp_path / "runlog.jsonl")


def abrir(runlog: RunLog, criticidad: str = "media"):
    return runlog.abrir_caso(tipo="cotizacion", referencia="CL-01/R-MTY-CDMX", criticidad=criticidad)


def test_caso_recorre_la_maquina_de_estados(runlog):
    caso = abrir(runlog)
    assert caso.estado == "recibido"

    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.registrar_paso(caso.trace_id, actor="svc-pricing", tipo="llamada_servicio")
    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    runlog.transicionar(caso.trace_id, "esperando_humano", actor="Ana", motivo="margen bajo objetivo")
    final = entregar(runlog, caso.trace_id, actor="Ana")

    assert final.estado == "entregado"
    assert final.cerrado
    assert final.pasos == 2  # la llamada al servicio y el paso de entrega


def test_transicion_invalida_se_rechaza_runlog(runlog):
    caso = abrir(runlog)

    with pytest.raises(TransicionInvalida) as excinfo:
        runlog.transicionar(caso.trace_id, "entregado", actor="D4-03")

    assert "recibido" in str(excinfo.value)


def test_maximo_dos_reintentos(runlog):
    """§12.3: dos reintentos. Al tercero el caso se bloquea y lo mira una persona."""
    caso = abrir(runlog)
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    for intento in range(MAX_REINTENTOS):
        runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
        runlog.transicionar(caso.trace_id, "rechazado_validacion", actor="svc-validation")
        runlog.registrar_paso(caso.trace_id, actor="D4-03", tipo="validacion", resultado="reintento")
        actual = runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
        assert actual.reintentos == intento + 1

    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    runlog.transicionar(caso.trace_id, "rechazado_validacion", actor="svc-validation")

    with pytest.raises(ReintentosAgotados):
        runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    bloqueado = runlog.transicionar(caso.trace_id, "bloqueado", actor="D4-03", motivo="reintentos agotados")
    assert bloqueado.estado == "bloqueado"


def test_registro_es_append_only(runlog):
    """El estado se reconstruye plegando eventos: nada se sobreescribe."""
    caso = abrir(runlog)
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.transicionar(caso.trace_id, "bloqueado", actor="D4-03", motivo="falta el precio del diesel")

    lineas = runlog.archivo.read_text(encoding="utf-8").strip().splitlines()

    assert len(lineas) == 3                       # apertura + dos transiciones
    assert '"evento": "apertura"' in lineas[0]
    assert runlog.caso(caso.trace_id).estado == "bloqueado"
    # Y el historial sigue completo: el caso pasó por en_proceso aunque ahora esté bloqueado.
    assert '"a": "en_proceso"' in lineas[1]


def test_eventos_sin_apertura_son_registro_corrupto(runlog, tmp_path):
    runlog.archivo.parent.mkdir(parents=True, exist_ok=True)
    runlog.archivo.write_text(
        '{"evento": "paso", "trace_id": "TR-X", "span_id": "TR-X.001", "actor": "D4-03",'
        ' "tipo": "ruteo", "ts": "2026-08-18T10:00:00+00:00"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ErrorDeIntegridad):
        runlog.casos()


def test_progreso_responde_sin_llm(runlog):
    """§8.2: estado, responsable, tiempo en el estado y siguiente paso, sin invocar un modelo."""
    caso = abrir(runlog, "alta")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.transicionar(caso.trace_id, "esperando_validacion", actor="svc-validation")
    runlog.transicionar(caso.trace_id, "esperando_humano", actor="Nay")

    progreso = runlog.progreso(caso.trace_id)

    assert progreso.estado == "esperando_humano"
    assert progreso.responsable == "Nay"
    assert progreso.siguiente_paso == "espera aprobacion en la bandeja de HITL"
    assert progreso.vence_en is not None          # sólo el que espera a un humano tiene SLA
    assert progreso.minutos_en_estado >= 0
    assert runlog.progreso(caso.trace_id).reintentos == 0


def test_consumo_por_actor_alimenta_budget(runlog):
    caso = abrir(runlog)
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.registrar_paso(caso.trace_id, actor="D4-03", tipo="llamada_llm", tokens=1200, costo_mxn="0.42")
    runlog.registrar_paso(caso.trace_id, actor="D4-03", tipo="llamada_llm", tokens=800, costo_mxn="0.28")
    runlog.registrar_paso(caso.trace_id, actor="svc-pricing", tipo="llamada_servicio")

    consumo = runlog.consumo()

    assert consumo["D4-03"]["tokens"] == 2000
    assert consumo["D4-03"]["costo_mxn"] == Decimal("0.70")
    assert consumo["svc-pricing"]["costo_mxn"] == Decimal("0.00")   # el código cuesta cero
    assert runlog.consumo(periodo="1999-01") == {}


def test_reintentos_por_actor_delatan_al_que_acierta_al_segundo(runlog):
    """Sin este registro, un agente que falla siempre al primer intento se ve perfecto."""
    caso = abrir(runlog)
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.registrar_paso(caso.trace_id, actor="D4-03", tipo="validacion", resultado="reintento")
    runlog.registrar_paso(caso.trace_id, actor="D4-03", tipo="validacion", resultado="ok")

    assert runlog.reintentos_por_actor() == {"D4-03": 1}


# --- SLA (§7.3) -----------------------------------------------------------


def test_calendario_corre_en_hora_local():
    """Los timestamps son UTC; la jornada es de Monterrey. Sin convertir, el SLA queda de madrugada."""
    manana_utc = datetime(2026, 8, 18, 13, 45, tzinfo=timezone.utc)   # 07:45 en Monterrey
    tarde_utc = datetime(2026, 8, 18, 19, 45, tzinfo=timezone.utc)    # 13:45 en Monterrey

    assert not es_habil(manana_utc)
    assert es_habil(tarde_utc)
    # Antes de abrir, el reloj arranca a las 9:00 locales: 9 + 4 = 13:00 local = 19:00Z.
    assert sumar_horas_habiles(manana_utc, 4) == datetime(2026, 8, 18, 19, 0, tzinfo=timezone.utc)


def test_sla_alta_en_horas_habiles():
    viernes_tarde = datetime(2026, 8, 21, 17, 0, tzinfo=HUSO)        # viernes 17:00, cierra a las 18

    vence = sumar_horas_habiles(viernes_tarde, 4)

    # Una hora el viernes y tres el lunes: el SLA no corre el fin de semana.
    assert vence == datetime(2026, 8, 24, 12, 0, tzinfo=HUSO)
    assert vence.weekday() == 0


def test_hitl_vencido_escala_nunca_aprueba():
    """La regla dura: un HITL vencido escala o expira. Nunca auto-aprueba."""
    espera = datetime(2026, 8, 18, 10, 0, tzinfo=HUSO)
    tarde = espera + timedelta(days=1)

    primero = resolver_vencimiento(
        trace_id="TR-1", criticidad="alta", espera_desde=espera, ahora=tarde, escalamientos=0
    )
    despues = resolver_vencimiento(
        trace_id="TR-1", criticidad="alta", espera_desde=espera, ahora=tarde, escalamientos=1
    )

    assert primero.accion == "escalar"
    assert despues.accion == "bloquear"
    assert {primero.accion, despues.accion} <= set(ACCIONES)
    assert "aprob" not in (primero.motivo + despues.motivo).lower()


def test_no_vencido_no_devuelve_nada():
    espera = datetime(2026, 8, 18, 10, 0, tzinfo=HUSO)

    assert resolver_vencimiento(
        trace_id="TR-1", criticidad="alta", espera_desde=espera, ahora=espera + timedelta(hours=1)
    ) is None


def test_criticidad_baja_expira():
    espera = datetime(2026, 8, 18, 10, 0, tzinfo=HUSO)
    mucho_despues = espera + timedelta(days=10)

    vencido = resolver_vencimiento(
        trace_id="TR-1", criticidad="baja", espera_desde=espera, ahora=mucho_despues
    )

    assert vencido.accion == "expirar"
    assert "no_atendido" in vencido.motivo


def test_aplicar_vencimiento_escala_y_luego_bloquea(runlog):
    caso = abrir(runlog, "alta")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")
    runlog.transicionar(caso.trace_id, "esperando_humano", actor="Nay")
    dentro_de_una_semana = datetime.now(timezone.utc) + timedelta(days=7)

    primero = runlog.vencidos(momento=dentro_de_una_semana)
    assert primero[0].accion == "escalar"
    tras_escalar = runlog.aplicar_vencimiento(primero[0])
    assert tras_escalar.estado == "esperando_humano"      # escalar no cierra: sigue esperando
    assert tras_escalar.escalamientos == 1

    segundo = runlog.vencidos(momento=dentro_de_una_semana)
    assert segundo[0].accion == "bloquear"
    assert runlog.aplicar_vencimiento(segundo[0]).estado == "bloqueado"


def test_solo_vence_lo_que_espera_a_un_humano(runlog):
    caso = abrir(runlog, "alta")
    runlog.transicionar(caso.trace_id, "en_proceso", actor="D4-03")

    assert runlog.vencidos(momento=datetime.now(timezone.utc) + timedelta(days=30)) == []
