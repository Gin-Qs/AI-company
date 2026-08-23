"""Genera los vectores dorados de `convocar()`, el contrato del puerto de la vista 8.

MISMA IDEA QUE `vectores_sla.py`, y por la misma razon. El portal reimplementa en TypeScript
las reglas de `agents/runtime.py:convocar()`, y una reimplementacion que nadie contrasta
diverge en silencio. El modo de fallo no es un error: es que el portal deje convocar a un
agente que el CLI habria rechazado, y el sistema quede con dos respuestas a "¿se puede
convocar a D4-03?".

Este script llama al Python **de verdad**, agente por agente, y anota que decide. El test de
TypeScript exige el mismo veredicto para el mismo agente. Si alguien relaja una regla en un
lado, la suite se pone roja en el otro.

Se ejecuta contra el registro real, sin base de datos y sin escribir nada en `office/`:
`office.encargos.DIRECTORIO` se redirige a un temporal, porque el unico camino que llega a
crear un encargo es el que sale bien, y este script no debe dejar rastro.

    python scripts/vectores_convocatoria.py

El resultado se versiona en `tests/fixtures/convocatoria-vectores.json` y la CI comprueba que
siga al dia, igual que con los vectores del SLA.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(RAIZ))

from agents import runtime  # noqa: E402
from agents.perfiles import cargar_perfiles  # noqa: E402
from office import encargos as encargos_mod  # noqa: E402
from office import estado as estado_mod  # noqa: E402

DESTINO = RAIZ / "tests" / "fixtures" / "convocatoria-vectores.json"

# El nombre del motivo en TypeScript para cada excepcion de Python. Es el contrato: los dos
# lados tienen que estar de acuerdo en QUE clase de "no" es cada uno.
MOTIVO = {
    "OficinaEnPausa": "oficina_en_pausa",
    "AgenteRetirado": "agente_retirado",
    "AgenteSinEncender": "agente_sin_encender",
    "AgenteNoDisponible": "agente_no_disponible",
    "PermisoDenegado": "permiso_denegado",
    "EncargoAmbiguo": "encargo_ambiguo",
}

# Un encargo completo. Los casos de encargo incompleto se generan aparte, para que el vector
# de cada agente aisle la regla del agente y no la del formulario.
COMPLETO = {
    "titulo": "Encargo de prueba para los vectores",
    "descripcion": "Modulo: vectores. Problema: el puerto puede divergir. Restriccion: ninguna.",
    "entregable_esperado": "Un JSON con el veredicto de cada agente.",
}

# Quien convoca en los vectores. Gabriel aparece en todos los `invocable_por` del registro,
# asi que con el se aislan las reglas de estado; con alguien que NO aparece se prueba el
# permiso. Los dos casos se generan.
QUIENES = ["Gabriel", "Nadie"]


def veredicto(agente_id: str, convocado_por: str, borrador: dict) -> dict:
    """Que decide el Python para esta combinacion. `ok` o el motivo del rechazo."""
    try:
        runtime.convocar(agente_id, convocado_por=convocado_por, **borrador)
    except Exception as error:  # noqa: BLE001 - se clasifica por tipo, a proposito
        nombre = type(error).__name__
        if nombre not in MOTIVO:
            raise
        return {"puede": False, "motivo": MOTIVO[nombre]}
    return {"puede": True}


def generar() -> dict:
    perfiles = cargar_perfiles()

    with tempfile.TemporaryDirectory() as temporal:
        # Ni un encargo real. El unico camino que crea uno es el que sale bien.
        encargos_mod.DIRECTORIO = Path(temporal)
        # La pausa se fija en "abierta" para que los vectores aislen las reglas del agente.
        # El caso de oficina en pausa se prueba aparte, en la unitaria de TypeScript: aqui
        # taparia todos los demas veredictos, porque gana sobre todo.
        estado_original = estado_mod.leer_pausa
        estado_mod.leer_pausa = lambda: {"activa": False}
        runtime.leer_pausa = lambda: {"activa": False}
        try:
            vectores = []
            for agente_id in sorted(perfiles):
                for quien in QUIENES:
                    vectores.append(
                        {
                            "agente": agente_id,
                            "convocado_por": quien,
                            "encargo_completo": True,
                            **veredicto(agente_id, quien, COMPLETO),
                        }
                    )

            # Y el formulario a medias, sobre un agente que sí se puede convocar: aisla la
            # regla del encargo ambiguo de las reglas del agente.
            convocables = [a for a in sorted(perfiles) if perfiles[a].disponible]
            for agente_id in convocables[:1]:
                for campo in ("titulo", "descripcion", "entregable_esperado"):
                    incompleto = {**COMPLETO, campo: "   "}
                    vectores.append(
                        {
                            "agente": agente_id,
                            "convocado_por": "Gabriel",
                            "encargo_completo": False,
                            "campo_vacio": campo,
                            **veredicto(agente_id, "Gabriel", incompleto),
                        }
                    )
        finally:
            estado_mod.leer_pausa = estado_original

    return {
        "generado_por": "scripts/vectores_convocatoria.py",
        "que_es": (
            "El veredicto de agents/runtime.py:convocar() para cada agente del registro. "
            "El puerto de TypeScript (web/lib/convocar.ts) tiene que dar el mismo."
        ),
        "borrador_completo": COMPLETO,
        "vectores": vectores,
    }


def main() -> int:
    datos = generar()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    conteo: dict[str, int] = {}
    for v in datos["vectores"]:
        clave = "ok" if v["puede"] else v["motivo"]
        conteo[clave] = conteo.get(clave, 0) + 1
    print(f"{len(datos['vectores'])} vectores -> {DESTINO.relative_to(RAIZ)}")
    for clave, n in sorted(conteo.items()):
        print(f"  {clave}: {n}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
