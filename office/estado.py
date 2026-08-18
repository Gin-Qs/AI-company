"""Estado de la oficina: lo que ve el plano en pixeles.

Junta registro, identidad, memoria, encargos y bitacora en un solo diccionario serializable.
Es la unica fuente que consume la interfaz: si algo no esta aqui, no se dibuja — y si esta
aqui, salio de un archivo del repositorio, no de una animacion decorativa.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from agents import memoria as memoria_mod
from agents.perfiles import cargar_identidades, cargar_perfiles
from office import bitacora
from office.encargos import Encargo, cargar_todos, por_agente

RAIZ = Path(__file__).resolve().parent.parent
PAUSA = RAIZ / "office" / "pausa.yaml"

# Como se ve cada situacion en el plano.
POSTURAS = {
    "pausado": "en pausa",
    "bloqueado": "levanta la mano",
    "en_curso": "tecleando",
    "pendiente": "leyendo el encargo",
    "libre": "disponible",
    "vacante": "silla vacia",
}


def leer_pausa() -> dict:
    """La pausa de la oficina, si la hay. Un archivo ausente significa oficina abierta."""
    if not PAUSA.is_file():
        return {"activa": False}
    datos = yaml.safe_load(PAUSA.read_text(encoding="utf-8")) or {}
    # YAML convierte `desde: 2026-08-18` en un date, que no es serializable a JSON y
    # viaja embebido en el plano. Se normaliza aqui, no en cada consumidor.
    normalizados = {
        clave: valor if isinstance(valor, (str, bool, int, float, list, dict, type(None))) else str(valor)
        for clave, valor in datos.items()
    }
    normalizados["activa"] = bool(datos.get("activa"))
    return normalizados


def _postura(quien, encargos: list[Encargo], pausada: bool = False) -> str:
    if not quien.disponible:
        return "vacante"
    if pausada:
        # La pausa gana sobre el trabajo abierto: el encargo sigue ahi, pero nadie lo esta
        # trabajando, y el plano no debe sugerir lo contrario.
        return "pausado"
    abiertos = [e for e in encargos if e.abierto]
    if any(e.estado == "bloqueado" for e in abiertos):
        return "bloqueado"
    if any(e.estado == "en_curso" for e in abiertos):
        return "en_curso"
    if abiertos:
        return "pendiente"
    return "libre"


def construir() -> dict:
    perfiles = cargar_perfiles()
    encargos_por_agente = por_agente()
    todos_encargos = cargar_todos()
    identidades = cargar_identidades()
    pausa = leer_pausa()

    agentes = []
    for agente_id, quien in sorted(perfiles.items()):
        if not quien.identidad:
            continue  # sin identidad no tiene lugar en el plano
        mios = encargos_por_agente.get(agente_id, [])
        memoria = memoria_mod.leer(agente_id)
        postura = _postura(quien, mios, pausa['activa'])
        datos = quien.as_dict()
        datos.update(
            {
                "postura": postura,
                "postura_texto": POSTURAS[postura],
                "encargos": [e.as_dict() for e in mios],
                "abiertos": sum(1 for e in mios if e.abierto),
                "memoria": {
                    "habilidades": memoria.habilidades or quien.habilidades,
                    "notas": [n.as_dict() for n in memoria.recientes(6)],
                    "total_notas": len(memoria.notas),
                },
            }
        )
        agentes.append(datos)

    encargos = [e.as_dict() for e in sorted(todos_encargos.values(), key=lambda e: e.id)]
    hechos = sum(1 for e in todos_encargos.values() if e.estado == "hecho")

    return {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pausa": pausa,
        "zonas": identidades.get("zonas") or {},
        "agentes": agentes,
        "encargos": encargos,
        "bitacora": [e.as_dict() for e in bitacora.leer(40)][::-1],
        "resumen": {
            "agentes": len(agentes),
            "disponibles": sum(1 for a in agentes if a["disponible"]),
            "encargos": len(encargos),
            "abiertos": sum(1 for e in todos_encargos.values() if e.abierto),
            "bloqueados": sum(1 for e in todos_encargos.values() if e.estado == "bloqueado"),
            "en_curso": sum(1 for e in todos_encargos.values() if e.estado == "en_curso"),
            "hechos": hechos,
            "avance_pct": round(100 * hechos / len(encargos)) if encargos else 0,
        },
    }


def resumen_texto() -> str:
    estado = construir()
    r = estado["resumen"]
    pausa = estado.get("pausa") or {}
    lineas = [
        ("OFICINA EN PAUSA desde " + str(pausa.get("desde")) + " por " + str(pausa.get("por")))
        if pausa.get("activa")
        else "Oficina abierta",
        f"Oficina virtual - {r['disponibles']}/{r['agentes']} agentes disponibles",
        f"Encargos: {r['abiertos']} abiertos ({r['en_curso']} en curso, {r['bloqueados']} bloqueados), "
        f"{r['hechos']} hechos - avance {r['avance_pct']}%",
        "",
    ]
    for agente in estado["agentes"]:
        marca = {"bloqueado": "!", "en_curso": ">", "pendiente": ".", "libre": " ",
                 "vacante": "-", "pausado": "="}[agente["postura"]]
        titulo = next((e["titulo"] for e in agente["encargos"] if e["estado"] in ("bloqueado", "en_curso")), "")
        lineas.append(
            f" {marca} {agente['nombre']:<8} {agente['id']:<6} {agente['postura_texto']:<18} {titulo[:44]}"
        )
    return "\n".join(lineas)
