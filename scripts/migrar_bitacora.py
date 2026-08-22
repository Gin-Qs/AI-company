"""Importa la bitacora vieja del office (JSONL propio) al registro de svc-runlog.

Por que existe: la bitacora del office fue el precursor declarado de `svc-runlog`. Con el
servicio construido, mantener dos registros seria justo lo que la arquitectura no permite —
dos respuestas posibles a "¿que le paso a este caso?" sin nadie que garantice que cuadran.

Que hace, exactamente:

  * Lee `office/bitacora.jsonl` **sin modificarlo**. Un registro append-only no se reescribe:
    el archivo se queda como esta y deja de recibir escrituras nuevas.
  * Reproduce cada evento contra `svc-runlog` conservando su `trace_id` y su fecha original.
    Rellenar las fechas con la de la importacion convertiria el historico en ruido.
  * Es idempotente: si los traces ya estan en el registro, no importa nada y lo dice.

    python scripts/migrar_bitacora.py [--simular]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover - conveniencia al correrlo suelto
    sys.path.insert(0, str(RAIZ))

from office import bitacora  # noqa: E402
from services.runlog import RunLog  # noqa: E402


def leer_historico(origen: Path) -> list[dict]:
    if not origen.is_file():
        return []
    return [json.loads(linea) for linea in origen.read_text(encoding="utf-8").splitlines() if linea.strip()]


def migrar(origen: Path | None = None, *, simular: bool = False) -> dict[str, int]:
    """Devuelve cuantos eventos se importaron, cuantos se omitieron y cuantos habia."""
    fuente = origen or bitacora.HISTORICO
    eventos = leer_historico(fuente)
    if not eventos:
        return {"leidos": 0, "importados": 0, "omitidos": 0}

    existentes = set(RunLog(bitacora.ARCHIVO).casos())
    importados = 0
    omitidos = 0

    for evento in eventos:
        if evento["trace_id"] in existentes:
            omitidos += 1
            continue
        if simular:
            importados += 1
            continue
        bitacora.registrar(
            evento=evento["evento"],
            agente=evento["agente"],
            encargo=evento.get("encargo", "-"),
            detalle=evento.get("detalle", ""),
            autor=evento.get("autor", "sistema"),
            trace_id=evento["trace_id"],
            ts=evento["ts"],
        )
        importados += 1

    return {"leidos": len(eventos), "importados": importados, "omitidos": omitidos}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migra la bitacora del office a svc-runlog.")
    parser.add_argument("--origen", default=str(bitacora.HISTORICO))
    parser.add_argument("--simular", action="store_true", help="cuenta sin escribir nada")
    args = parser.parse_args(argv)

    resumen = migrar(Path(args.origen), simular=args.simular)
    print(
        f"{resumen['leidos']} eventos en el historico - "
        f"{resumen['importados']} importados, {resumen['omitidos']} ya estaban"
    )
    if resumen["omitidos"] and not resumen["importados"]:
        print("nada que hacer: el historico ya vive en svc-runlog")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
