"""Crea un agente nuevo, entero y coherente, en un solo comando.

    python scripts/nuevo_agente.py --id D3-01 --nombre "Planeacion de Rutas" \\
        --departamento 03-operaciones --equipo T03-01 --fase 5 \\
        --persona Lucia --mision "Arma la programacion semanal de rutas."

POR QUE EXISTE. Dar de alta un agente toca CINCO archivos, y el orden importa:

    1. registry/policies/roadmap.yaml   el roadmap manda: "un ID que no este aqui no
                                        puede aparecer en ningun registro"
    2. registry/agents/<ID>-<slug>.yaml el contrato
    3. registry/teams/<EQUIPO>.yaml     el equipo lo adopta
    4. office/identidades.yaml          nombre, voz y escritorio en el plano
    5. agents/memoria/<ID>.md           su memoria, vacia pero existente

Hacerlo a mano son cinco oportunidades de equivocarse, y el error tipico —crear el
contrato y olvidar el roadmap— no se ve hasta que el validador falla por otra cosa.
Este script hace los cinco y despues corre el validador: si el agente nuevo rompe
alguna regla, te enteras en el mismo comando y no tres commits despues.

POR QUE NO USA PyYAML PARA ESCRIBIR. `roadmap.yaml` e `identidades.yaml` estan llenos de
comentarios que explican decisiones, y `yaml.safe_dump` los borra todos. Un archivo de
politica sin sus comentarios es un archivo que nadie va a entender en seis meses. Asi que
se insertan lineas de texto en el sitio correcto, no se reescribe el archivo.

El agente nace en estado `planned`: existe en el roadmap y todavia no se puede convocar.
Pasarlo a `listo` exige declarar sus condiciones de encendido (regla 13), y eso es una
decision, no un valor por defecto.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
ROADMAP = RAIZ / "registry" / "policies" / "roadmap.yaml"
DIR_AGENTES = RAIZ / "registry" / "agents"
DIR_EQUIPOS = RAIZ / "registry" / "teams"
IDENTIDADES = RAIZ / "office" / "identidades.yaml"
DIR_MEMORIA = RAIZ / "agents" / "memoria"

FORMATO_ID = re.compile(r"^D[1-8]-\d{2}$")

# El plano de office/oficina.html mide 16 x 9 tiles.
ANCHO, ALTO = 16, 9

TIERS = ("Alto", "Medio", "Bajo")
ESTILOS = ("corto", "largo", "chongo", "gorra")

# Paleta del pixel art. Se rota para que dos agentes nuevos no salgan identicos.
PALETA = [
    {"piel": "#c98d63", "pelo": "#3b2415", "ropa": "#c2543d", "acento": "#f0b429"},
    {"piel": "#e0ac7e", "pelo": "#1c1c1c", "ropa": "#3f7fbf", "acento": "#8fd3f4"},
    {"piel": "#8d5a3b", "pelo": "#2b1d12", "ropa": "#4b6b52", "acento": "#a8d5a2"},
    {"piel": "#a86b45", "pelo": "#5a2d0c", "ropa": "#7a4fa3", "acento": "#d9b3ff"},
]


class Rechazado(SystemExit):
    """El alta no procede. Se explica por que y no se toca ningun archivo."""


def _slug(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plano.lower()).strip("-")


def _cargar(ruta: Path) -> dict:
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


# --- comprobaciones previas -------------------------------------------------


def comprobar(args) -> tuple[dict, Path]:
    """Todo lo que puede impedir el alta, antes de escribir el primer byte."""
    if not FORMATO_ID.match(args.id):
        raise Rechazado(f"'{args.id}' no tiene forma de agente de dominio (D#-##, por ejemplo D3-01).")

    existente = list(DIR_AGENTES.glob(f"{args.id}-*.yaml"))
    if existente:
        raise Rechazado(f"{args.id} ya existe: {existente[0].relative_to(RAIZ)}")

    equipo = DIR_EQUIPOS / f"{args.equipo}-*.yaml"
    equipos = list(DIR_EQUIPOS.glob(f"{args.equipo}-*.yaml"))
    if not equipos:
        raise Rechazado(
            f"el equipo {args.equipo} no existe en registry/teams/. "
            f"Un agente sin equipo no tiene owner humano, y sin owner humano su HITL no "
            f"tiene a donde llegar (authority-gate.yaml -> hitl.ruteo)."
        )

    identidades = _cargar(IDENTIDADES)
    if args.id in (identidades.get("agentes") or {}):
        raise Rechazado(f"{args.id} ya tiene identidad en office/identidades.yaml")

    zonas = identidades.get("zonas") or {}
    if args.zona not in zonas:
        raise Rechazado(
            f"la zona '{args.zona}' no existe. Zonas declaradas: {', '.join(sorted(zonas))}. "
            f"Si el agente necesita una zona nueva, se agrega primero a office/identidades.yaml."
        )

    return identidades, equipos[0]


def escritorio_libre(identidades: dict) -> dict[str, int]:
    """Un tile que no ocupe nadie. Dos agentes en la misma silla se dibujan encima."""
    ocupados = {
        (d.get("escritorio", {}).get("x"), d.get("escritorio", {}).get("y"))
        for d in (identidades.get("agentes") or {}).values()
    }
    for y in range(2, ALTO):
        for x in range(1, ANCHO):
            if (x, y) not in ocupados:
                return {"x": x, "y": y}
    raise Rechazado("no queda un solo tile libre en el plano: hay que agrandarlo antes de crear otro agente.")


# --- escritura --------------------------------------------------------------


def escribir_roadmap(args) -> None:
    """El roadmap primero: es la regla que el propio archivo declara."""
    texto = ROADMAP.read_text(encoding="utf-8")
    if re.search(rf"^\s+{re.escape(args.id)}:", texto, re.MULTILINE):
        return  # ya estaba; el alta puede venir de un roadmap escrito a mano

    linea = f'  {args.id}: {{nombre: "{args.nombre}", fase: {args.fase}}}\n'
    familia = args.id.split("-")[0]                       # D3 de D3-01
    hermanos = list(re.finditer(rf"^  {familia}-\d{{2}}:.*\n", texto, re.MULTILINE))
    if hermanos:
        corte = hermanos[-1].end()                        # tras el ultimo de su departamento
    else:
        servicios = re.search(r"^servicios:", texto, re.MULTILINE)
        if not servicios:
            raise Rechazado("roadmap.yaml no tiene bloque `servicios:`; no se donde termina `agentes:`.")
        corte = servicios.start()
        linea = linea + "\n"
    ROADMAP.write_text(texto[:corte] + linea + texto[corte:], encoding="utf-8")


def escribir_contrato(args) -> Path:
    destino = DIR_AGENTES / f"{args.id}-{_slug(args.nombre)}.yaml"
    destino.write_text(
        f"""id: {args.id}
name: {args.nombre}
department: {args.departamento}
teams:
  - {args.equipo}
mission: >
  {args.mision}

# Nace `planned`: declarado en el roadmap y sin poder convocarse. Pasarlo a `listo` exige
# escribir sus condiciones_encendido (regla 13 del validador); pasarlo a `built` exige
# haberlas cumplido. El estado no se sube a mano sin cerrar lo que el estado promete.
estado: planned
fase: {args.fase}
model_tier: {args.tier}

# Quien puede convocarlo. O1 no existe hasta la fase 4; hasta entonces el ruteo es una
# persona, que es lo que la arquitectura dice que debe ser.
invocable_por: [{args.convocable}]

# Servicios que ya existen y este agente puede usar. Un agente `listo` o `built` no puede
# depender de un servicio `planned` (regla 8): mientras tanto, van en tools_planeadas.
tools: []
tools_planeadas: []

inputs: []
outputs: []

# Ningun agente tiene ACT-* por defecto: se otorga uno por uno, con umbral, y todo ACT-*
# necesita al menos un CTL-* que lo controle (regla 3).
actions: []
controls: []

# Lo que NO hace. Un limite que no esta escrito no existe.
limits: []

prompt: agents/prompts/{args.id}.md
memoria: agents/memoria/{args.id}.md
prompt_version: v1.0.0
""",
        encoding="utf-8",
    )
    return destino


def escribir_equipo(args, ruta_equipo: Path) -> None:
    texto = ruta_equipo.read_text(encoding="utf-8")
    datos = yaml.safe_load(texto) or {}
    actuales = [str(a) for a in (datos.get("agentes") or [])]
    if args.id in actuales:
        return
    nuevos = actuales + [args.id]
    lista = "[" + ", ".join(nuevos) + "]"
    if re.search(r"^agentes:", texto, re.MULTILINE):
        texto = re.sub(r"^agentes:.*$", f"agentes: {lista}", texto, count=1, flags=re.MULTILINE)
    else:
        texto = texto.rstrip("\n") + f"\nagentes: {lista}\n"
    ruta_equipo.write_text(texto, encoding="utf-8")


def escribir_identidad(args, identidades: dict) -> None:
    sitio = escritorio_libre(identidades)
    paleta = PALETA[len(identidades.get("agentes") or {}) % len(PALETA)]
    bloque = f"""
  {args.id}:
    nombre: {args.persona}
    puesto: "{args.nombre}"
    lema: "{args.lema}"
    voz: "{args.voz}"
    escritorio: {{x: {sitio['x']}, y: {sitio['y']}}}
    zona: {args.zona}
    sprite: {{piel: "{paleta['piel']}", pelo: "{paleta['pelo']}", ropa: "{paleta['ropa']}", acento: "{paleta['acento']}", estilo: {args.estilo}}}
"""
    IDENTIDADES.write_text(
        IDENTIDADES.read_text(encoding="utf-8").rstrip("\n") + "\n" + bloque, encoding="utf-8"
    )


def escribir_memoria(args) -> Path:
    DIR_MEMORIA.mkdir(parents=True, exist_ok=True)
    destino = DIR_MEMORIA / f"{args.id}.md"
    destino.write_text(
        f"""# Memoria - {args.persona} ({args.id}) - {args.nombre}

## Habilidades


## Notas

""",
        encoding="utf-8",
    )
    return destino


# --- orquestacion -----------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Da de alta un agente nuevo, entero y validado.")
    p.add_argument("--id", required=True, help="D#-## (por ejemplo D3-01)")
    p.add_argument("--nombre", required=True, help="el puesto, no la persona")
    p.add_argument("--departamento", required=True, help="por ejemplo 03-operaciones")
    p.add_argument("--equipo", required=True, help="T##-## existente en registry/teams/")
    p.add_argument("--mision", required=True)
    p.add_argument("--fase", type=int, required=True)
    p.add_argument("--persona", required=True, help="el nombre humano del agente en el plano")
    p.add_argument("--tier", default="Medio", choices=TIERS)
    p.add_argument("--zona", default="operaciones")
    p.add_argument("--estilo", default="corto", choices=ESTILOS)
    p.add_argument("--lema", default="", help="su forma de trabajar en una frase")
    p.add_argument("--voz", default="", help="como habla y que persigue")
    p.add_argument("--convocable", default="Gabriel", help="lista separada por comas")
    p.add_argument("--dry-run", action="store_true", help="dice que haria y no toca nada")
    args = p.parse_args(argv)

    identidades, ruta_equipo = comprobar(args)

    if args.dry_run:
        print(f"Crearia {args.id} ({args.persona}) en {args.equipo}, fase {args.fase}:")
        for r in (
            ROADMAP,
            DIR_AGENTES / f"{args.id}-{_slug(args.nombre)}.yaml",
            ruta_equipo,
            IDENTIDADES,
            DIR_MEMORIA / f"{args.id}.md",
        ):
            print(f"  {r.relative_to(RAIZ)}")
        print(f"  escritorio libre: {escritorio_libre(identidades)}")
        return 0

    escribir_roadmap(args)
    contrato = escribir_contrato(args)
    escribir_equipo(args, ruta_equipo)
    escribir_identidad(args, identidades)
    memoria = escribir_memoria(args)

    print(f"{args.id} dado de alta:")
    for r in (ROADMAP, contrato, ruta_equipo, IDENTIDADES, memoria):
        print(f"  {r.relative_to(RAIZ)}")

    # El alta no termina al escribir: termina cuando el registro sigue siendo coherente.
    print("\nValidando el registro...")
    codigo = subprocess.call([sys.executable, str(RAIZ / "scripts" / "validate_registry.py")])
    if codigo != 0:
        print(
            f"\nEl agente quedo escrito y el registro NO esta en verde. Revisa las fallas de "
            f"arriba antes de commitear: lo mas probable es que falte completar tools, "
            f"outputs o limits en {contrato.relative_to(RAIZ)}."
        )
    return codigo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
