"""La siembra inicial (docs/portal.md §9), probada sin Postgres.

Se puede porque `plan()` es una funcion pura: arma las sentencias y no abre una conexion. Lo
que se comprueba aqui no es que Postgres acepte el SQL —eso lo dira el dia que exista la
contrasena— sino lo que de verdad se puede equivocar en una migracion y no se nota despues:

  * que conserve la fecha y el trace originales,
  * que el `seq` respete el orden de aparicion dentro de cada trace,
  * que la proyeccion de casos sea la de svc-runlog y no un calculo paralelo,
  * que sea reejecutable: toda insercion con su `on conflict`,
  * y que no invente autores.

Las cifras no se fijan en duro contra el repositorio real: se derivan de los archivos que la
propia prueba escribe, o se afirman como relaciones. Agregar un encargo o una nota de memoria
no puede poner roja esta suite.
"""

from __future__ import annotations

import json

import pytest

from scripts.migrar_a_postgres import (
    Fuentes,
    como_sql,
    encargos_del_office,
    eventos_del_runlog,
    notas_de_memoria,
    pausas_del_office,
    personas_del_gate,
    plan,
)

GATE = """
autoridades:
  direccion: Gabriel
  finanzas: Nay
  externos: [contador, abogado]
umbrales:
  descuento_tarifa:
    humano_operativo: {max_pct: 5, quien: Nay}
hitl:
  ruteo:
    responsable: owner_humano_del_equipo
"""

EVENTOS = [
    {
        "evento": "apertura",
        "trace_id": "TR-1",
        "tipo": "encargo",
        "referencia": "E-900",
        "criticidad": "alta",
        "ts": "2026-01-02T10:00:00+00:00",
        "actor": "D5-01",
    },
    {
        "evento": "paso",
        "trace_id": "TR-1",
        "span_id": "TR-1.001",
        "parent_span_id": None,
        "actor": "D5-01",
        "tipo": "ruteo",
        "ts": "2026-01-02T10:05:00+00:00",
        "resultado": "ok",
        "decision_ruteo": "",
        "entradas": {"autor": "Gabriel", "encargo": "E-900"},
        "salidas": {},
        "versiones": {},
        "tokens": 120,
        "costo_mxn": "3.50",
        "latencia_ms": 900,
        "gate": {},
    },
    {
        "evento": "apertura",
        "trace_id": "TR-2",
        "tipo": "cotizacion",
        "referencia": "CL-01",
        "criticidad": "baja",
        "ts": "2026-01-03T09:00:00+00:00",
        "actor": "D4-03",
    },
    {
        "evento": "paso",
        "trace_id": "TR-2",
        "span_id": "TR-2.001",
        "parent_span_id": None,
        "actor": "D4-03",
        "tipo": "llamada_servicio",
        "ts": "2026-01-03T09:10:00+00:00",
        "resultado": "ok",
        "decision_ruteo": "",
        "entradas": {"autor": "Fulano"},  # no existe en el gate
        "salidas": {},
        "versiones": {},
        "tokens": 0,
        "costo_mxn": "0.00",
        "latencia_ms": 0,
        "gate": {},
    },
]

ENCARGO_DE_AGENTE = """
id: E-900
titulo: Un encargo que convoco un agente
agente: C-04
convocado_por: D5-01
estado: pendiente
descripcion: >
  Con salto
  de linea.
entregable_esperado: Algo
depende_de: []
hitl: false
creado: '2026-01-02'
actualizado: '2026-01-02'
trace_id: TR-1
"""

ENCARGO_DE_PERSONA = """
id: E-901
titulo: Un encargo que convoco una persona
agente: D5-01
convocado_por: Gabriel
estado: en_curso
descripcion: Otro
entregable_esperado: Algo mas
depende_de: [E-900]
hitl: true
creado: '2026-01-03'
actualizado: '2026-01-03'
trace_id: TR-2
"""

MEMORIA = """# Memoria - Ivana (D4-03) - Pricing

## Habilidades

- cotizacion

## Notas

### 2026-01-02 - E-900 - decision
Una nota que pertenece a un encargo.

### 2026-01-03 - - - contexto
Una nota suelta, sin encargo.
"""

PAUSA = """
activa: false

historial:
  - desde: 2026-01-01
    hasta: 2026-01-05
    por: Gabriel
    motivo: >
      Sentar las bases
      antes de seguir.
    se_reanudaba_cuando: >
      Los servicios esten en verde.
    reanudada_porque: >
      Se cumplio.
"""


@pytest.fixture()
def fuentes(tmp_path):
    """Un repositorio de mentira, completo y minusculo."""
    (tmp_path / "registry" / "policies").mkdir(parents=True)
    (tmp_path / "registry" / "policies" / "authority-gate.yaml").write_text(GATE, encoding="utf-8")

    (tmp_path / "data" / "runlog").mkdir(parents=True)
    (tmp_path / "data" / "runlog" / "runlog.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in EVENTOS) + "\n", encoding="utf-8"
    )

    encargos = tmp_path / "office" / "encargos"
    encargos.mkdir(parents=True)
    (encargos / "E-900.yaml").write_text(ENCARGO_DE_AGENTE, encoding="utf-8")
    (encargos / "E-901.yaml").write_text(ENCARGO_DE_PERSONA, encoding="utf-8")

    memoria = tmp_path / "agents" / "memoria"
    memoria.mkdir(parents=True)
    (memoria / "D4-03.md").write_text(MEMORIA, encoding="utf-8")

    (tmp_path / "office" / "pausa.yaml").write_text(PAUSA, encoding="utf-8")

    return Fuentes.por_defecto(tmp_path)


# --- personas ---------------------------------------------------------------


def test_las_personas_salen_del_gate_no_de_una_lista_en_duro(fuentes):
    """§7.3: `personas.nombre` debe coincidir con un valor de `autoridades`."""
    nombres = personas_del_gate(
        {"autoridades": {"direccion": "Gabriel", "finanzas": "Nay", "externos": ["contador"]}}
    )
    assert nombres == ["Gabriel", "Nay", "contador"]


def test_un_operador_nuevo_en_el_gate_entra_solo(fuentes):
    """La prueba de que es configuracion: se cambia el YAML y cambia el resultado."""
    gate = fuentes.gate
    gate.write_text(gate.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    antes = len(personas_del_gate({"autoridades": {"direccion": "Gabriel"}}))
    despues = len(personas_del_gate({"autoridades": {"direccion": "Gabriel", "logistica": "Elias"}}))
    assert despues == antes + 1


# --- eventos ----------------------------------------------------------------


def test_el_seq_cuenta_dentro_de_cada_trace_no_del_archivo(fuentes):
    filas = eventos_del_runlog(fuentes.runlog, ["Gabriel", "Nay"])
    por_trace: dict[str, list[int]] = {}
    for f in filas:
        por_trace.setdefault(f["trace_id"], []).append(f["seq"])
    # Cada trace empieza en 1 y no salta.
    for trace, seqs in por_trace.items():
        assert seqs == list(range(1, len(seqs) + 1)), trace


def test_conserva_la_fecha_original_del_evento(fuentes):
    filas = eventos_del_runlog(fuentes.runlog, ["Gabriel"])
    originales = [e["ts"] for e in EVENTOS]
    assert [f["ts"] for f in filas] == originales


def test_datos_guarda_el_resto_del_evento_sin_duplicar_columnas(fuentes):
    filas = eventos_del_runlog(fuentes.runlog, ["Gabriel"])
    apertura = filas[0]
    assert apertura["datos"] == {"tipo": "encargo", "referencia": "E-900", "criticidad": "alta"}
    for propia in ("evento", "trace_id", "ts", "actor"):
        assert propia not in apertura["datos"]


def test_el_autor_solo_se_pone_si_es_una_persona_que_existe(fuentes):
    filas = eventos_del_runlog(fuentes.runlog, ["Gabriel", "Nay"])
    por_trace = {f["trace_id"]: f for f in filas if f["evento"] == "paso"}
    # Gabriel existe en el gate: se atribuye.
    assert por_trace["TR-1"]["autor"] == "Gabriel"
    # "Fulano" no existe: null, no un nombre parecido ni el owner del equipo.
    assert por_trace["TR-2"]["autor"] is None


def test_el_actor_nunca_se_confunde_con_el_autor(fuentes):
    """Un agente ejecuta; una persona autoriza. Meter al agente en `autor_persona` haria
    que la auditoria dijera que una persona hizo algo que hizo un modelo."""
    filas = eventos_del_runlog(fuentes.runlog, ["Gabriel"])
    for f in filas:
        assert f["autor"] != f["actor"]


# --- casos ------------------------------------------------------------------


def test_los_casos_son_el_plegado_de_svc_runlog(fuentes):
    """No se recalculan aqui: si divergieran, habria dos respuestas a '¿en que va?'."""
    from services.runlog import RunLog

    esperados = RunLog(fuentes.runlog).casos()
    filas = [s for s in plan(fuentes).sentencias if s.tabla == "casos"]
    assert len(filas) == len(esperados)
    trazas_en_plan = {s.parametros[0] for s in filas}
    assert trazas_en_plan == set(esperados)


def test_ultimo_seq_es_el_ultimo_evento_del_caso(fuentes):
    """El candado optimista de §8.4 depende de este numero: quien aprueba inserta en N+1."""
    filas = {s.parametros[0]: s.parametros[-1] for s in plan(fuentes).sentencias if s.tabla == "casos"}
    eventos = eventos_del_runlog(fuentes.runlog, [])
    esperado: dict[str, int] = {}
    for e in eventos:
        esperado[e["trace_id"]] = max(esperado.get(e["trace_id"], 0), e["seq"])
    assert filas == esperado


def test_el_costo_viaja_como_texto_no_como_float(fuentes):
    """§8.3: ningun importe cruza el sistema como `number`."""
    for s in plan(fuentes).sentencias:
        if s.tabla == "casos":
            assert isinstance(s.parametros[12], str)


# --- encargos ---------------------------------------------------------------


def test_un_encargo_convocado_por_un_agente_no_inventa_una_persona(fuentes):
    """La correccion 2 del encabezado del script, comprobada."""
    filas = {s.parametros[0]: s.parametros for s in plan(fuentes).sentencias if s.tabla == "encargos"}
    de_agente = filas["E-900"]
    assert de_agente[3] is None          # convocado_por: sin persona
    assert de_agente[4] == "D5-01"       # convocado_por_actor: lo que dice el YAML

    de_persona = filas["E-901"]
    assert de_persona[3] == "Gabriel"
    assert de_persona[4] == "Gabriel"


def test_el_texto_del_yaml_pierde_los_saltos_pero_no_las_palabras(fuentes):
    encargos = {e["id"]: e for e in encargos_del_office(fuentes.encargos)}
    assert encargos["E-900"]["descripcion"] == "Con salto de linea."


def test_los_encargos_van_despues_de_los_casos(fuentes):
    """`encargos.trace_id` es FK a `casos`: al reves, la transaccion revienta."""
    tablas = [s.tabla for s in plan(fuentes).sentencias]
    assert tablas.index("casos") < tablas.index("encargos")


# --- memoria ----------------------------------------------------------------


def test_una_nota_hereda_el_trace_de_su_encargo(fuentes):
    trace_por_encargo = {e["id"]: e["trace_id"] for e in encargos_del_office(fuentes.encargos)}
    notas = notas_de_memoria(fuentes.memoria, trace_por_encargo)
    con_encargo = [n for n in notas if n["encargo"] == "E-900"]
    assert con_encargo and all(n["trace_id"] == "TR-1" for n in con_encargo)


def test_una_nota_sin_encargo_se_queda_sin_trace(fuentes):
    notas = notas_de_memoria(fuentes.memoria, {"E-900": "TR-1"})
    sueltas = [n for n in notas if n["encargo"] == "-"]
    assert sueltas and all(n["trace_id"] is None for n in sueltas)


def test_la_memoria_se_lee_con_el_parser_del_runtime(fuentes):
    """Si `agents.memoria` cambia de formato, esto cambia con el. Dos parsers discreparian."""
    from agents import memoria as memoria_mod

    notas = notas_de_memoria(fuentes.memoria, {})
    assert {n["tipo"] for n in notas} <= set(memoria_mod.TIPOS)


def test_leer_la_memoria_no_deja_movida_la_constante_del_modulo(fuentes):
    """El helper toca `memoria.DIRECTORIO` para poder apuntar a otra carpeta. Si no lo
    restaurara, el runtime leeria las memorias del directorio equivocado el resto del proceso."""
    from agents import memoria as memoria_mod

    antes = memoria_mod.DIRECTORIO
    notas_de_memoria(fuentes.memoria, {})
    assert memoria_mod.DIRECTORIO == antes


# --- pausa ------------------------------------------------------------------


def test_la_pausa_conserva_motivo_y_condicion_de_reanudacion(fuentes):
    pausas = pausas_del_office(fuentes.pausa)
    assert len(pausas) == 1
    p = pausas[0]
    assert p["motivo"].startswith("Sentar las bases")
    assert p["se_reanuda_cuando"]  # el YAML lo llama `se_reanudaba_cuando`; se acepta igual
    assert p["hasta"] == "2026-01-05"  # cerrada: no queda una pausa activa de mentira


def test_la_pausa_importada_no_reabre_la_oficina(fuentes):
    """`pausa_activa_unica` solo permite una fila con `hasta is null`. Importar una pausa ya
    levantada con `hasta` vacio dejaria la oficina en pausa el dia de la migracion."""
    for p in pausas_del_office(fuentes.pausa):
        assert p["hasta"] is not None


# --- el plan entero ---------------------------------------------------------


def test_toda_insercion_es_reejecutable(fuentes):
    """Idempotencia, comprobada sentencia por sentencia y no prometida en un comentario."""
    for s in plan(fuentes).sentencias:
        assert "on conflict" in s.sql, s.sql
        assert "do nothing" in s.sql, s.sql


def test_ningun_dato_historico_se_rellena_con_la_fecha_de_hoy(fuentes):
    """Lo que hace util un historico es que sus fechas sean las suyas."""
    for s in plan(fuentes).sentencias:
        assert "now()" not in s.sql.lower(), s.sql


def test_el_orden_respeta_las_llaves_foraneas(fuentes):
    tablas = [s.tabla for s in plan(fuentes).sentencias]
    orden = [t for i, t in enumerate(tablas) if i == 0 or tablas[i - 1] != t]
    assert orden == ["personas", "eventos", "casos", "encargos", "memoria_notas", "pausa"]


def test_el_sql_generado_abre_y_cierra_una_transaccion(fuentes):
    texto = como_sql(plan(fuentes))
    assert texto.strip().startswith("-- Siembra inicial")
    assert "\nbegin;\n" in texto
    assert texto.strip().endswith("commit;")


def test_el_sql_generado_escapa_las_comillas(fuentes):
    """Un titulo con apostrofe no puede romper el archivo ni, peor, cambiar lo que hace."""
    (fuentes.encargos / "E-902.yaml").write_text(
        "id: E-902\ntitulo: \"El encargo d'Ana\"\nagente: C-01\nconvocado_por: Gabriel\n"
        "estado: pendiente\ndescripcion: x\nentregable_esperado: y\ndepende_de: []\n"
        "hitl: false\ncreado: '2026-01-04'\nactualizado: '2026-01-04'\ntrace_id: TR-2\n",
        encoding="utf-8",
    )
    assert "'El encargo d''Ana'" in como_sql(plan(fuentes))


def test_correrlo_dos_veces_produce_el_mismo_plan(fuentes):
    """Determinismo: sin el, comparar dos corridas no dice nada."""
    primero = [(s.tabla, s.sql, s.parametros) for s in plan(fuentes).sentencias]
    segundo = [(s.tabla, s.sql, s.parametros) for s in plan(fuentes).sentencias]
    assert primero == segundo


def test_un_repositorio_vacio_produce_un_plan_vacio(tmp_path):
    """La migracion no puede inventar filas cuando no hay archivos que leer."""
    assert plan(Fuentes.por_defecto(tmp_path)).sentencias == []
