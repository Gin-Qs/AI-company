"""La siembra inicial de Postgres (docs/portal.md §9).

Lleva a la base lo que hoy vive en archivos y que a partir del portal deja de vivir ahi:
personas, el registro de eventos, la proyeccion de casos, los encargos, las notas de memoria
y el historial de pausa. `registry/` NO se toca: los contratos siguen en git, cambian por PR
y el portal solo los lee (§3).

Tres disciplinas, y las tres se notan en el codigo:

  * **Conserva la fecha y el trace originales.** Un registro que se rellena con la fecha de la
    importacion deja de servir para reconstruir el pasado. Ningun `now()` entra en los datos
    historicos; los `ts` salen del archivo.
  * **Es idempotente.** Correrla dos veces no duplica nada: cada insercion lleva su
    `on conflict do nothing` sobre la clave natural que ya declara el esquema.
  * **No inventa la proyeccion.** Los `casos` no se calculan aqui: se piden a
    `services.runlog.RunLog.casos()`, que es el mismo plegado que usa el resto del sistema.
    Reimplementarlo seria construir la segunda verdad que este documento existe para evitar.

Separacion a proposito entre armar y escribir: `plan()` es una funcion pura que devuelve
sentencias con sus parametros, sin tocar la red. Por eso se puede probar entera sin Postgres,
que es lo unico que hoy se puede probar (la contrasena de la base todavia no existe, §15).

    python scripts/migrar_a_postgres.py --simular          # cuenta y no escribe
    python scripts/migrar_a_postgres.py --sql siembra.sql  # deja el SQL, no se conecta
    python scripts/migrar_a_postgres.py                    # escribe, usando DATABASE_URL

TRES COSAS QUE EL PLAN DECLARABA DISTINTO, y que se corrigen aqui porque los datos mandan:

  1. `§9` dice "12 casos". Son **18**: `data/runlog/runlog.jsonl` tiene 18 traces. Doce son
     los encargos; los otros seis son casos que no nacieron de un encargo.
  2. `§6` declara `encargos.convocado_por` como FK obligatoria a `personas`. Nueve de los doce
     encargos los convoco **D5-01**, que es un agente, no una persona. Se corrige el esquema,
     no el dato: `convocado_por` pasa a ser opcional y se agrega `convocado_por_actor`, que
     guarda lo que el YAML dice literalmente. Ver `scripts/sql/0002-convocado-por-actor.sql`.
  3. `eventos.autor_persona` se llena **solo** cuando el evento nombra a una persona que existe
     en el gate (`entradas.autor`). Los pasos que ejecuto un agente quedan en null: poner ahi
     al owner humano del equipo seria atribuirle una accion que no hizo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover - conveniencia al correrlo suelto
    sys.path.insert(0, str(RAIZ))

import yaml  # noqa: E402

from agents import memoria as memoria_mod  # noqa: E402
from services.runlog import RunLog  # noqa: E402

# --- de donde sale cada cosa -------------------------------------------------


@dataclass(frozen=True)
class Fuentes:
    """Los archivos que se leen. Parametrizables para poder probar en `tmp_path`."""

    gate: Path
    runlog: Path
    encargos: Path
    memoria: Path
    pausa: Path

    @classmethod
    def por_defecto(cls, raiz: Path = RAIZ) -> "Fuentes":
        return cls(
            gate=raiz / "registry" / "policies" / "authority-gate.yaml",
            runlog=raiz / "data" / "runlog" / "runlog.jsonl",
            encargos=raiz / "office" / "encargos",
            memoria=raiz / "agents" / "memoria",
            pausa=raiz / "office" / "pausa.yaml",
        )


@dataclass(frozen=True)
class Sentencia:
    """Una insercion con sus parametros. `tabla` es solo para contar y para el resumen."""

    tabla: str
    sql: str
    parametros: tuple[Any, ...]


@dataclass
class Plan:
    sentencias: list[Sentencia] = field(default_factory=list)

    def agregar(self, tabla: str, sql: str, parametros: Sequence[Any]) -> None:
        self.sentencias.append(Sentencia(tabla, " ".join(sql.split()), tuple(parametros)))

    def por_tabla(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for s in self.sentencias:
            conteo[s.tabla] = conteo.get(s.tabla, 0) + 1
        return conteo


def _leer_yaml(ruta: Path) -> dict[str, Any]:
    if not ruta.is_file():
        return {}
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


# --- 1. personas -------------------------------------------------------------

# `personas.nombre` debe coincidir con un valor de `autoridades` (§7.3), asi que la lista no
# se escribe aqui: se deriva del gate. Si manana entra un cuarto operador al YAML, la siembra
# lo trae sin que nadie edite este archivo.
def personas_del_gate(gate: dict[str, Any]) -> list[str]:
    autoridades = gate.get("autoridades") or {}
    nombres: list[str] = []
    for clave, valor in autoridades.items():
        if clave == "externos":
            continue
        if isinstance(valor, str) and valor.strip():
            nombres.append(valor.strip())
    # Los externos son etiquetas de puesto (contador, abogado), no nombres propios. Entran
    # igual: §7.3 dice que un contador entra al portal con `nombre = "contador"`.
    for etiqueta in gate.get("autoridades", {}).get("externos") or []:
        nombres.append(str(etiqueta).strip())
    # Sin duplicados y en orden estable, para que dos corridas produzcan el mismo plan.
    vistos: set[str] = set()
    return [n for n in nombres if not (n in vistos or vistos.add(n))]


# `invitada_por` se queda en null a proposito: nadie invito a estas seis filas, las sembro una
# migracion. Poner ahi a Gabriel seria escribir un hecho que no ocurrio.
SQL_PERSONA = """
    insert into personas (nombre) values (%s)
    on conflict (nombre) do nothing
"""

# Una persona no se referencia por uuid desde el script: se busca por nombre en la misma
# sentencia. Asi la siembra no necesita leer de vuelta lo que acaba de escribir, y sigue
# siendo idempotente aunque los uuid cambien entre corridas.
REF_PERSONA = "(select id from personas where nombre = %s)"


# --- 2. eventos --------------------------------------------------------------

COLUMNAS_PROPIAS = {"evento", "trace_id", "ts", "actor"}


def _autor_persona(evento: dict[str, Any], personas: Iterable[str]) -> str | None:
    """El nombre de la persona que hizo esto, si el evento nombra a una que existe.

    Solo `entradas.autor` cuenta. Un `actor` es un agente o un servicio; atribuirle el paso
    al owner humano de su equipo convertiria una suposicion en un dato de auditoria.
    """
    autor = (evento.get("entradas") or {}).get("autor")
    if isinstance(autor, str) and autor.strip() in set(personas):
        return autor.strip()
    return None


def eventos_del_runlog(runlog: Path, personas: Sequence[str]) -> list[dict[str, Any]]:
    """Los eventos con su `seq` asignado por orden de aparicion dentro de cada trace (§9)."""
    if not runlog.is_file():
        return []

    contador: dict[str, int] = {}
    filas: list[dict[str, Any]] = []
    for linea in runlog.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        evento = json.loads(linea)
        trace_id = evento["trace_id"]
        contador[trace_id] = contador.get(trace_id, 0) + 1
        filas.append(
            {
                "trace_id": trace_id,
                "seq": contador[trace_id],
                "evento": evento["evento"],
                "ts": evento["ts"],
                "actor": evento.get("actor", ""),
                "autor": _autor_persona(evento, personas),
                # `datos` guarda el evento completo menos lo que ya es columna. Nada se pierde
                # y nada se duplica: el jsonb es el resto, no una copia.
                "datos": {k: v for k, v in evento.items() if k not in COLUMNAS_PROPIAS},
            }
        )
    return filas


SQL_EVENTO_CON_AUTOR = f"""
    insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
    values (%s, %s, %s, %s, %s, {REF_PERSONA}, %s::jsonb)
    on conflict (trace_id, seq) do nothing
"""

SQL_EVENTO_SIN_AUTOR = """
    insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
    values (%s, %s, %s, %s, %s, null, %s::jsonb)
    on conflict (trace_id, seq) do nothing
"""


# --- 3. casos ----------------------------------------------------------------

SQL_CASO = """
    insert into casos (trace_id, tipo, referencia, criticidad, estado, responsable,
                       abierto_en, actualizado_en, reintentos, escalamientos, pasos,
                       tokens, costo_mxn, ultimo_seq)
    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    on conflict (trace_id) do nothing
"""


# --- 4. encargos -------------------------------------------------------------


def _texto(valor: Any) -> str:
    """YAML con `>` deja saltos de linea que no significan nada. Se normalizan."""
    return " ".join(str(valor or "").split())


def encargos_del_office(carpeta: Path) -> list[dict[str, Any]]:
    if not carpeta.is_dir():
        return []
    filas = []
    for archivo in sorted(carpeta.glob("*.yaml")):
        d = _leer_yaml(archivo)
        if not d.get("id"):
            continue
        filas.append(
            {
                "id": str(d["id"]),
                "titulo": _texto(d.get("titulo")),
                "agente": str(d.get("agente", "")),
                "convocado_por": str(d.get("convocado_por", "")),
                "estado": str(d.get("estado", "pendiente")),
                "descripcion": _texto(d.get("descripcion")),
                "entregable_esperado": _texto(d.get("entregable_esperado")),
                "depende_de": [str(x) for x in (d.get("depende_de") or [])],
                "hitl": bool(d.get("hitl", False)),
                "trace_id": str(d.get("trace_id", "")),
                "creado_en": str(d.get("creado", "")),
                "actualizado_en": str(d.get("actualizado", "")),
            }
        )
    return filas


SQL_ENCARGO = f"""
    insert into encargos (id, titulo, agente, convocado_por, convocado_por_actor, estado,
                          descripcion, entregable_esperado, depende_de, hitl, trace_id,
                          creado_en, actualizado_en)
    values (%s, %s, %s, {REF_PERSONA}, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    on conflict (id) do nothing
"""


# --- 5. notas de memoria -----------------------------------------------------


def notas_de_memoria(carpeta: Path, trace_por_encargo: dict[str, str]) -> list[dict[str, Any]]:
    """Las notas de `agents/memoria/*.md`, con el trace que hereda de su encargo.

    El parser NO se reimplementa: es `agents.memoria.leer`, el mismo que usa el runtime para
    armar el prompt. Dos lecturas distintas del mismo archivo terminarian discrepando.
    """
    if not carpeta.is_dir():
        return []
    filas = []
    for archivo in sorted(carpeta.glob("*.md")):
        agente = archivo.stem
        memoria = _leer_memoria(carpeta, agente)
        for nota in memoria.notas:
            encargo = nota.encargo if nota.encargo and nota.encargo != "-" else "-"
            filas.append(
                {
                    "agente": agente,
                    "fecha": nota.fecha,
                    "encargo": encargo,
                    "tipo": nota.tipo,
                    "texto": nota.texto,
                    # El trace no esta escrito en la nota: se hereda del encargo, que es como
                    # lo escribe `runtime.recordar()` (la nota y el caso comparten trace).
                    "trace_id": trace_por_encargo.get(encargo),
                }
            )
    return filas


def _leer_memoria(carpeta: Path, agente: str):
    """`memoria.leer` resuelve la ruta con su propia constante; aqui se necesita parametrizable."""
    original = memoria_mod.DIRECTORIO
    try:
        memoria_mod.DIRECTORIO = carpeta
        return memoria_mod.leer(agente)
    finally:
        memoria_mod.DIRECTORIO = original


# Una nota no tiene clave natural en el esquema (§6): `memoria_notas` es bigserial y nada mas.
# Sin una, correr la siembra dos veces duplicaria las notas. Se le da una clave natural con un
# indice unico —ver scripts/sql/0002— sobre lo que de verdad identifica a una nota: quien la
# escribio, cuando, sobre que encargo, de que tipo y que dice.
SQL_NOTA = """
    insert into memoria_notas (agente, fecha, encargo, tipo, texto, trace_id)
    values (%s, %s, %s, %s, %s, %s)
    on conflict (agente, fecha, encargo, tipo, md5(texto)) do nothing
"""


# --- 6. pausa ----------------------------------------------------------------


def pausas_del_office(ruta: Path) -> list[dict[str, Any]]:
    """El historial de `office/pausa.yaml`. Una fila por pausa, con su levantamiento dentro."""
    datos = _leer_yaml(ruta)
    filas = []
    for entrada in datos.get("historial") or []:
        filas.append(
            {
                "desde": _fecha(entrada.get("desde")),
                "hasta": _fecha(entrada.get("hasta")),
                "por": str(entrada.get("por", "")),
                "motivo": _texto(entrada.get("motivo")),
                # El YAML lo llama `se_reanudaba_cuando` en pasado porque ya se levanto; la
                # columna es `se_reanuda_cuando`. Se aceptan los dos nombres.
                "se_reanuda_cuando": _texto(
                    entrada.get("se_reanuda_cuando") or entrada.get("se_reanudaba_cuando")
                ),
                "reanudada_porque": _texto(entrada.get("reanudada_porque")) or None,
            }
        )
    return filas


def _fecha(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)


# `pausa` tampoco tiene clave natural. Se le da una: no puede haber dos pausas que empiecen en
# el mismo instante (indice unico sobre `desde`, en scripts/sql/0002).
SQL_PAUSA = f"""
    insert into pausa (desde, hasta, por, motivo, se_reanuda_cuando, reanudada_por, reanudada_porque)
    values (%s, %s, {REF_PERSONA}, %s, %s, null, %s)
    on conflict (desde) do nothing
"""


# --- el plan completo --------------------------------------------------------


def plan(fuentes: Fuentes | None = None) -> Plan:
    """Todo lo que hay que escribir, en orden, sin escribir nada. Funcion pura."""
    f = fuentes or Fuentes.por_defecto()
    p = Plan()

    # 1. Personas primero: los cinco pasos siguientes las referencian por nombre.
    personas = personas_del_gate(_leer_yaml(f.gate))
    for nombre in personas:
        p.agregar("personas", SQL_PERSONA, [nombre])

    # 2. Eventos. El registro; todo lo demas es proyeccion de esto.
    for e in eventos_del_runlog(f.runlog, personas):
        datos = json.dumps(e["datos"], ensure_ascii=False)
        if e["autor"]:
            p.agregar(
                "eventos",
                SQL_EVENTO_CON_AUTOR,
                [e["trace_id"], e["seq"], e["evento"], e["ts"], e["actor"], e["autor"], datos],
            )
        else:
            p.agregar(
                "eventos",
                SQL_EVENTO_SIN_AUTOR,
                [e["trace_id"], e["seq"], e["evento"], e["ts"], e["actor"], datos],
            )

    # 3. Casos: el plegado de svc-runlog, no un calculo nuevo.
    ultimo_seq: dict[str, int] = {}
    for e in eventos_del_runlog(f.runlog, personas):
        ultimo_seq[e["trace_id"]] = max(ultimo_seq.get(e["trace_id"], 0), int(e["seq"]))

    for caso in RunLog(f.runlog).casos().values():
        p.agregar(
            "casos",
            SQL_CASO,
            [
                caso.trace_id,
                caso.tipo,
                caso.referencia,
                caso.criticidad,
                caso.estado,
                caso.responsable,
                caso.abierto_en,
                caso.actualizado_en,
                caso.reintentos,
                caso.escalamientos,
                caso.pasos,
                caso.tokens,
                # El dinero cruza como texto, nunca como float (§8.3). psycopg lo entrega a
                # `numeric` sin pasar por binario de punto flotante.
                str(Decimal(str(caso.costo_mxn))),
                ultimo_seq.get(caso.trace_id, 0),
            ],
        )

    # 4. Encargos. Van despues de `casos` porque su `trace_id` es FK.
    encargos = encargos_del_office(f.encargos)
    for e in encargos:
        # `convocado_por` solo se llena si quien convoco es una persona. Cuando fue D5-01
        # —nueve de los doce— la FK queda en null y el nombre del agente vive en
        # `convocado_por_actor`. Ver el encabezado de este archivo, correccion 2.
        es_persona = e["convocado_por"] in set(personas)
        p.agregar(
            "encargos",
            SQL_ENCARGO,
            [
                e["id"],
                e["titulo"],
                e["agente"],
                e["convocado_por"] if es_persona else None,
                e["convocado_por"],
                e["estado"],
                e["descripcion"],
                e["entregable_esperado"],
                e["depende_de"],
                e["hitl"],
                e["trace_id"],
                e["creado_en"],
                e["actualizado_en"],
            ],
        )

    # 5. Notas de memoria, con el trace heredado de su encargo.
    trace_por_encargo = {e["id"]: e["trace_id"] for e in encargos if e["trace_id"]}
    for n in notas_de_memoria(f.memoria, trace_por_encargo):
        p.agregar(
            "memoria_notas",
            SQL_NOTA,
            [n["agente"], n["fecha"], n["encargo"], n["tipo"], n["texto"], n["trace_id"]],
        )

    # 6. Pausa.
    for pa in pausas_del_office(f.pausa):
        p.agregar(
            "pausa",
            SQL_PAUSA,
            [
                pa["desde"],
                pa["hasta"],
                pa["por"],
                pa["motivo"],
                pa["se_reanuda_cuando"],
                pa["reanudada_porque"],
            ],
        )

    return p


# --- escribir ----------------------------------------------------------------


def _literal(valor: Any) -> str:
    """Un valor como literal de SQL. Solo para `--sql`, que es para leer y revisar."""
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float, Decimal)):
        return str(valor)
    if isinstance(valor, list):
        return "array[" + ", ".join(_literal(v) for v in valor) + "]::text[]"
    return "'" + str(valor).replace("'", "''") + "'"


def como_sql(p: Plan) -> str:
    """El plan como un archivo SQL revisable, con la transaccion alrededor."""
    lineas = [
        "-- Siembra inicial del portal de mando (docs/portal.md §9).",
        "-- Generado por scripts/migrar_a_postgres.py --sql. No se edita a mano.",
        "-- Idempotente: cada insercion lleva su on conflict do nothing.",
        "begin;",
        "",
    ]
    for s in p.sentencias:
        partes = s.sql.split("%s")
        armado = "".join(
            parte + (_literal(valor) if i < len(s.parametros) else "")
            for i, (parte, valor) in enumerate(
                zip(partes, list(s.parametros) + [None] * (len(partes) - len(s.parametros)))
            )
        )
        lineas.append(armado + ";")
    lineas += ["", "commit;", ""]
    return "\n".join(lineas)


def ejecutar(p: Plan, dsn: str) -> dict[str, int]:
    """Escribe el plan en una sola transaccion. Si algo falla, no queda nada a medias."""
    try:
        import psycopg  # noqa: PLC0415 - opcional a proposito: `pip install -e ".[postgres]"`
    except ModuleNotFoundError as falta:  # pragma: no cover - depende del entorno
        raise SystemExit(
            "falta psycopg. Instalalo con: pip install -e \".[postgres]\"\n"
            "O corre con --sql para generar el archivo y aplicarlo por otro medio."
        ) from falta

    escritas: dict[str, int] = {}
    with psycopg.connect(dsn) as conexion:
        with conexion.cursor() as cursor:
            for s in p.sentencias:
                cursor.execute(s.sql, s.parametros)
                # rowcount = 0 significa "ya estaba": el on conflict lo absorbio.
                escritas[s.tabla] = escritas.get(s.tabla, 0) + (cursor.rowcount or 0)
        conexion.commit()
    return escritas


def _dsn() -> str:
    """La conexion directa, no el pooler: esto son sentencias de migracion (web/.env.example)."""
    for variable in ("DIRECT_URL", "DATABASE_URL"):
        valor = os.environ.get(variable, "").strip()
        if not valor:
            continue
        if "CONTRASENA" in valor or "PON_AQUI" in valor:
            raise SystemExit(
                f"{variable} todavia trae el marcador de la contrasena, no la contrasena.\n"
                "La genero Supabase al crear el proyecto por API y nadie la vio, asi que hay\n"
                "que RESTABLECERLA (no buscarla): Supabase -> Project Settings -> Database\n"
                "-> Reset database password. Mientras tanto: --simular o --sql."
            )
        return valor
    raise SystemExit(
        "no hay DIRECT_URL ni DATABASE_URL en el entorno.\n"
        "Se leen de web/.env.local; para correr esto: export DIRECT_URL=\"...\"\n"
        "Sin base de datos: --simular cuenta lo que haria, --sql deja el archivo."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra Postgres con lo que hoy vive en archivos.")
    parser.add_argument("--raiz", default=str(RAIZ))
    parser.add_argument("--simular", action="store_true", help="cuenta lo que haria, sin conectarse")
    parser.add_argument("--sql", metavar="ARCHIVO", help="escribe el SQL y no se conecta")
    args = parser.parse_args(argv)

    p = plan(Fuentes.por_defecto(Path(args.raiz)))
    conteo = p.por_tabla()
    resumen = ", ".join(f"{n} {tabla}" for tabla, n in conteo.items())

    if args.sql:
        destino = Path(args.sql)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(como_sql(p), encoding="utf-8")
        print(f"{len(p.sentencias)} sentencias -> {destino}")
        print(f"  {resumen}")
        return 0

    if args.simular:
        print(f"{len(p.sentencias)} sentencias listas, sin escribir nada")
        print(f"  {resumen}")
        return 0

    escritas = ejecutar(p, _dsn())
    nuevas = sum(escritas.values())
    print(f"{len(p.sentencias)} sentencias corridas, {nuevas} filas nuevas")
    for tabla, n in escritas.items():
        print(f"  {tabla}: {n} de {conteo.get(tabla, 0)}")
    if nuevas == 0:
        print("nada que hacer: la siembra ya estaba aplicada")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
