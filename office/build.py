"""Genera office/oficina.html incrustando el estado real.

Sin servidor y sin fetch: el archivo se abre con doble clic y funciona, porque el estado viaja
dentro. El precio es que hay que regenerarlo cuando algo cambia, y ese es justamente el momento
en que uno quiere mirar la oficina.
"""

from __future__ import annotations

import json
from pathlib import Path

from office.estado import construir

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "office" / "plantilla.html"
SALIDA = RAIZ / "office" / "oficina.html"
MARCA = "/*__ESTADO__*/"


def construir_html(estado: dict | None = None) -> str:
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    if MARCA not in plantilla:
        raise RuntimeError(f"la plantilla no tiene la marca {MARCA}")

    datos = json.dumps(estado or construir(), ensure_ascii=False, indent=1)
    # La marca precede al objeto por defecto; lo sustituimos entero.
    inicio = plantilla.index(MARCA)
    fin = plantilla.index("\n", inicio)
    linea = plantilla[inicio:fin]
    return plantilla.replace(linea, f"{MARCA}{datos};")


def escribir(destino: Path | None = None) -> Path:
    salida = destino or SALIDA
    salida.write_text(construir_html(), encoding="utf-8")
    return salida


if __name__ == "__main__":  # pragma: no cover
    print(escribir())
