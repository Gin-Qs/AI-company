"""Linea de comandos de la oficina virtual.

    python -m office.cli estado
    python -m office.cli convocar C-04 --titulo "..." --descripcion "..." --entregable "..." --por Gabriel
    python -m office.cli avanzar E-002 en_curso --autor Dalia --nota "empieza el esquema"
    python -m office.cli recordar C-04 "el esquema hereda las llaves de la Fase 0" --tipo decision --encargo E-002
    python -m office.cli build
"""

from __future__ import annotations

import argparse
import sys

from agents.runtime import (
    AgenteNoDisponible,
    EncargoAmbiguo,
    PermisoDenegado,
    convocar,
    escribir_prompts,
    recordar,
)
from office import encargos as encargos_mod
from office.entorno import EscrituraFueraDeLocal, exigir_local
from office.build import escribir
from office.estado import resumen_texto


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Oficina virtual: agentes, encargos y bitacora.")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("estado", help="resumen de quien esta haciendo que")

    convocatoria = sub.add_parser("convocar", help="abre un encargo para un agente")
    convocatoria.add_argument("agente")
    convocatoria.add_argument("--titulo", required=True)
    convocatoria.add_argument("--descripcion", required=True, help="modulo, problema y restriccion")
    convocatoria.add_argument("--entregable", required=True)
    convocatoria.add_argument("--por", required=True, help="quien convoca (Gabriel o D5-01)")
    convocatoria.add_argument("--depende-de", nargs="*", default=[])
    convocatoria.add_argument("--hitl", action="store_true", help="necesita aprobacion humana para cerrar")

    avance = sub.add_parser("avanzar", help="cambia el estado de un encargo")
    avance.add_argument("encargo")
    avance.add_argument("estado", choices=encargos_mod.ESTADOS)
    avance.add_argument("--autor", required=True)
    avance.add_argument("--nota", default="")

    memoria = sub.add_parser("recordar", help="escribe en la memoria de un agente")
    memoria.add_argument("agente")
    memoria.add_argument("texto")
    memoria.add_argument("--tipo", default="aprendizaje")
    memoria.add_argument("--encargo", default="-")

    sub.add_parser("build", help="regenera office/oficina.html y los prompts")

    args = parser.parse_args(argv)

    if args.comando == "estado":
        print(resumen_texto())
        return 0

    if args.comando == "convocar":
        try:
            exigir_local("convocar")
            encargo = convocar(
                args.agente,
                titulo=args.titulo,
                descripcion=args.descripcion,
                entregable_esperado=args.entregable,
                convocado_por=args.por,
                depende_de=args.depende_de,
                hitl=args.hitl,
            )
        except (EscrituraFueraDeLocal, PermisoDenegado, EncargoAmbiguo, AgenteNoDisponible, KeyError) as error:
            print(f"RECHAZADO: {error}", file=sys.stderr)
            return 2
        print(f"{encargo.id} abierto para {encargo.agente} - trace {encargo.trace_id}")
        return 0

    if args.comando == "avanzar":
        try:
            exigir_local("avanzar")
            encargo = encargos_mod.avanzar(args.encargo, args.estado, autor=args.autor, nota=args.nota)
        except (EscrituraFueraDeLocal, encargos_mod.TransicionInvalida, KeyError) as error:
            print(f"RECHAZADO: {error}", file=sys.stderr)
            return 2
        print(f"{encargo.id} -> {encargo.estado}")
        return 0

    if args.comando == "recordar":
        try:
            exigir_local("recordar")
            recordar(args.agente, args.texto, tipo=args.tipo, encargo=args.encargo)
        except (EscrituraFueraDeLocal, ValueError, KeyError) as error:
            print(f"RECHAZADO: {error}", file=sys.stderr)
            return 2
        print(f"memoria de {args.agente} actualizada")
        return 0

    if args.comando == "build":
        salida = escribir()
        prompts = escribir_prompts()
        print(f"{salida} generado - {len(prompts)} prompts actualizados")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
