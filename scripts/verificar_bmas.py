"""¿Se puede cerrar B+? Comprueba las condiciones y, si se cumplen, las cierra.

B+ es el punto del ejercicio: poner `cumplida: true` en la condición *"Bandeja única de HITL
del ERP en producción"* de los cinco agentes del MVP. Todo lo demás del portal fue
infraestructura para llegar aquí.

**Este script no cree en promesas: comprueba.** Cada condición se verifica contra el sistema
real —el registro, Postgres, la CI— y ninguna se da por buena porque alguien la diga. Sin
`--cerrar` sólo informa; nada se toca.

    python scripts/verificar_bmas.py            # dice qué falta
    python scripts/verificar_bmas.py --cerrar   # cierra la condición si TODO pasa

POR QUÉ HACE FALTA UN SCRIPT PARA CINCO LÍNEAS DE YAML. Porque cerrar la condición es
afirmar que la bandeja funciona en producción, y esa afirmación se puede escribir sin ser
verdad. Un `cumplida: true` puesto a mano no deja rastro de qué se comprobó; éste imprime la
evidencia de cada punto y se niega a cerrar si falta uno.

LO QUE NO PUEDE COMPROBAR SOLO, y por qué se pide a mano (§13.5): que dos personas aprobando
el mismo HITL a la vez den un ganador y un perdedor con **un** evento en el registro. Eso
necesita dos navegadores con dos sesiones de Clerk. El script comprueba las precondiciones y
el rastro que deja esa prueba, no la prueba misma.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(RAIZ))

import yaml  # noqa: E402

from services.common.postgres import BaseIlegible, consultar, dsn  # noqa: E402

CONDICION = "Bandeja única de HITL del ERP en producción"
AGENTES = RAIZ / "registry" / "agents"


@dataclass
class Punto:
    nombre: str
    ok: bool
    evidencia: str
    #: Qué hacer si falla. Un "no cumple" sin salida manda a adivinar.
    arreglo: str = ""


def _fila(sql: str, que: str):
    filas = consultar(sql, que=que)
    return filas[0] if filas else None


# --- las comprobaciones -----------------------------------------------------


def hay_base() -> Punto:
    return Punto(
        "Hay base de datos configurada",
        dsn() is not None,
        "DIRECT_URL/DATABASE_URL presente" if dsn() else "sin configurar",
        arreglo="export DIRECT_URL=... (de web/.env.local)",
    )


def suite_y_registro() -> Punto:
    """La CI tiene que estar en verde sobre `main`, y publicada. No se cree al script local:
    se lee lo que la CI escribió, que es lo que el portal enseña."""
    f = _fila(
        "select rama, left(commit_sha,8) as commit, en_falla, pytest_ok, pytest_total,"
        " corrido_en from validacion_registro where rama = 'main'"
        " order by corrido_en desc limit 1",
        "la última corrida de CI sobre main",
    )
    if not f:
        return Punto(
            "La CI publicó una corrida de main",
            False,
            "validacion_registro no tiene ninguna fila de main",
            arreglo="empuja a main y espera a que corra .github/workflows/validar.yml",
        )
    rama, commit, en_falla, pytest_ok, pytest_total, corrido = f
    ok = en_falla == 0 and bool(pytest_ok)
    return Punto(
        "CI de main en verde",
        ok,
        f"commit {commit}, {en_falla} reglas en falla, pytest "
        f"{'pasó' if pytest_ok else 'FALLÓ'} ({pytest_total} pruebas), {corrido:%Y-%m-%d %H:%M} UTC",
        arreglo="arregla lo que reporte la CI y vuelve a empujar",
    )


def oficina_abierta() -> Punto:
    f = _fila(
        "select motivo, se_reanuda_cuando from pausa where hasta is null limit 1",
        "la pausa de la oficina",
    )
    return Punto(
        "La oficina no está en pausa",
        f is None,
        "abierta" if f is None else f"EN PAUSA: {f[0]} — se reanuda cuando: {f[1]}",
        arreglo="levántala en /oficina (sólo Dirección, y exige decir por qué)",
    )


def dos_personas() -> Punto:
    """§13.5 pide dos navegadores con personas distintas. Con una sola cuenta vinculada no se
    puede provocar la carrera, y sin la carrera no se comprueba el candado de §8.4."""
    filas = consultar(
        "select nombre from personas where clerk_user_id is not null and activa order by nombre",
        que="las personas vinculadas a Clerk",
    )
    nombres = [f[0] for f in filas]
    return Punto(
        "Hay al menos dos personas vinculadas a Clerk",
        len(nombres) >= 2,
        f"{len(nombres)} vinculada(s): {', '.join(nombres) or 'ninguna'}",
        arreglo="invita a otra persona en Clerk y enlaza su clerk_user_id en `personas`",
    )


def hubo_un_hitl_resuelto() -> Punto:
    """La prueba de fuego: una transición a `entregado` o `bloqueado` escrita por una PERSONA.
    Es el rastro que deja aprobar o rechazar desde la bandeja. Sin eso, la bandeja está
    construida y nadie la ha usado nunca."""
    filas = consultar(
        "select e.trace_id, e.datos->>'a' as destino, p.nombre, e.ts"
        "  from eventos e join personas p on p.id = e.autor_persona"
        " where e.evento = 'transicion'"
        "   and e.datos->>'de' = 'esperando_humano'"
        " order by e.ts desc limit 5",
        que="los HITL resueltos por una persona",
    )
    if not filas:
        return Punto(
            "Alguien resolvió un HITL desde la bandeja",
            False,
            "ninguna transición desde esperando_humano con autor humano",
            arreglo="convoca un encargo con firma humana en /convocar y resuélvelo en /hitl",
        )
    trace, destino, quien, ts = filas[0]
    return Punto(
        "Alguien resolvió un HITL desde la bandeja",
        True,
        f"{len(filas)} resuelto(s); el último {trace} → {destino} por {quien} ({ts:%Y-%m-%d %H:%M} UTC)",
    )


def la_proyeccion_cuadra() -> Punto:
    """Si la proyección divergió del registro, cerrar B+ sería firmar sobre datos que no se
    pueden reconstruir. Es la misma consulta que `web/lib/db/proyeccion.test.ts`."""
    filas = consultar(
        """
        with plegado as (
          select trace_id,
                 count(*) filter (where evento='paso') as pasos,
                 max(seq) as ultimo_seq,
                 (array_agg(datos->>'a' order by seq desc)
                    filter (where evento='transicion'))[1] as estado,
                 (array_agg(actor order by seq desc))[1] as responsable
            from eventos group by trace_id)
        select c.trace_id from casos c join plegado p using (trace_id)
         where c.estado      is distinct from coalesce(p.estado,'recibido')
            or c.responsable is distinct from p.responsable
            or c.pasos       is distinct from p.pasos
            or c.ultimo_seq  is distinct from p.ultimo_seq
        """,
        que="la coherencia entre casos y eventos",
    )
    return Punto(
        "La proyección `casos` se puede replegar desde `eventos`",
        not filas,
        "coincide en todos los casos" if not filas else f"{len(filas)} caso(s) divergen: "
        + ", ".join(f[0] for f in filas[:5]),
        arreglo="repliega la proyección desde eventos; hay una ruta de escritura que no la mueve",
    )


def el_portal_responde() -> Punto:
    """En producción, no en localhost. La condición dice «en producción» con todas sus letras."""
    url = "https://ai-company-git-main-ga-s-projectss.vercel.app/"
    try:
        salida = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "25", url],
            capture_output=True, text=True, timeout=40,
        ).stdout.strip()
    except Exception as error:  # noqa: BLE001
        return Punto("El portal responde en producción", False, f"no se pudo consultar: {error}")
    # 302 es correcto: la proteccion de Vercel intercepta antes que la app.
    ok = salida in {"200", "302", "307", "401"}
    return Punto(
        "El portal responde en producción",
        ok,
        f"HTTP {salida} ({'protegido por Vercel' if salida == '302' else 'responde'})",
        arreglo="revisa el último despliegue en Vercel",
    )


COMPROBACIONES = [
    hay_base,
    el_portal_responde,
    suite_y_registro,
    la_proyeccion_cuadra,
    oficina_abierta,
    dos_personas,
    hubo_un_hitl_resuelto,
]


# --- cerrar la condición ----------------------------------------------------


def agentes_con_la_condicion() -> dict[Path, dict]:
    encontrados = {}
    for archivo in sorted(AGENTES.glob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
        for c in datos.get("condiciones_encendido") or []:
            if isinstance(c, dict) and CONDICION in str(c.get("condicion", "")):
                encontrados[archivo] = datos
                break
    return encontrados


def cerrar(archivos: dict[Path, dict]) -> list[str]:
    """Pone `cumplida: true` reescribiendo sólo esa línea.

    Se edita el texto y no se vuelca el YAML entero a propósito: `yaml.safe_dump` reordena
    claves y se come los comentarios, y estos archivos son contratos que la gente lee.
    """
    tocados = []
    for archivo in archivos:
        lineas = archivo.read_text(encoding="utf-8").splitlines()
        dentro = False
        for i, linea in enumerate(lineas):
            if CONDICION in linea:
                dentro = True
                continue
            if dentro:
                if linea.strip().startswith("cumplida:"):
                    sangria = linea[: len(linea) - len(linea.lstrip())]
                    lineas[i] = f"{sangria}cumplida: true"
                    tocados.append(archivo.name)
                    break
                # Otra condición empezó antes de encontrar `cumplida`: no se toca nada.
                if linea.strip().startswith("- condicion:"):
                    break
        archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return tocados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="¿Se puede cerrar B+?")
    parser.add_argument("--cerrar", action="store_true", help="pone cumplida: true si todo pasa")
    parser.add_argument("--json", metavar="ARCHIVO", help="escribe el resultado como JSON")
    args = parser.parse_args(argv)

    puntos: list[Punto] = []
    for comprobar in COMPROBACIONES:
        try:
            puntos.append(comprobar())
        except BaseIlegible as error:
            puntos.append(Punto(comprobar.__name__, False, f"no se pudo comprobar: {error}"))

    print("¿Se puede cerrar B+?\n" + "-" * 78)
    for p in puntos:
        print(f"[{'  OK  ' if p.ok else ' FALTA'}] {p.nombre}")
        print(f"         {p.evidencia}")
        if not p.ok and p.arreglo:
            print(f"         -> {p.arreglo}")

    faltan = [p for p in puntos if not p.ok]
    archivos = agentes_con_la_condicion()
    print("-" * 78)
    print(f"{len(puntos) - len(faltan)} de {len(puntos)} condiciones cumplidas · "
          f"{len(archivos)} agentes declaran la condición")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {"puede_cerrar": not faltan,
                 "puntos": [{"nombre": p.nombre, "ok": p.ok, "evidencia": p.evidencia} for p in puntos],
                 "agentes": [a.name for a in archivos]},
                ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    if faltan:
        print(f"\nNO se puede cerrar todavía: faltan {len(faltan)}.")
        return 1

    if not args.cerrar:
        print("\nTodo pasa. Corre con --cerrar para poner cumplida: true en los cinco agentes.")
        return 0

    tocados = cerrar(archivos)
    print(f"\ncerrada en {len(tocados)}: {', '.join(tocados)}")
    print("Ahora corre `python scripts/validate_registry.py` y abre el PR.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
