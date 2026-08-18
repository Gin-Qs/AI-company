"""Perfil de un agente: lo que dice el registro mas quien es en la oficina.

El registro (registry/) manda sobre la autoridad: mision, limites, ACT-*. La identidad
(office/identidades.yaml) manda sobre la presentacion: nombre, voz, escritorio. Este modulo
los junta en un solo objeto y no deja que se contradigan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
DIR_AGENTES = RAIZ / "registry" / "agents"
DIR_CONSULTORES = RAIZ / "registry" / "consultants"
IDENTIDADES = RAIZ / "office" / "identidades.yaml"


class PerfilDesconocido(KeyError):
    """Se pidio un agente que el registro no declara."""


@dataclass
class Perfil:
    agente_id: str
    tipo: str  # consultor | dominio
    puesto: str
    mision: str
    estado: str
    registro: dict = field(default_factory=dict)
    identidad: dict = field(default_factory=dict)

    # --- identidad -------------------------------------------------------

    @property
    def nombre(self) -> str:
        return str(self.identidad.get("nombre") or self.agente_id)

    @property
    def etiqueta(self) -> str:
        return f"{self.nombre} ({self.agente_id})"

    @property
    def lema(self) -> str:
        return str(self.identidad.get("lema") or "")

    @property
    def voz(self) -> str:
        return str(self.identidad.get("voz") or "")

    @property
    def zona(self) -> str:
        return str(self.identidad.get("zona") or "consultoria")

    @property
    def escritorio(self) -> dict:
        return dict(self.identidad.get("escritorio") or {"x": 0, "y": 0})

    @property
    def sprite(self) -> dict:
        return dict(self.identidad.get("sprite") or {})

    # --- autoridad -------------------------------------------------------

    @property
    def acciones(self) -> list[str]:
        registradas = self.registro.get("actions") or self.registro.get("acciones_act") or []
        return [str(a) for a in registradas]

    @property
    def es_consultor(self) -> bool:
        return self.tipo == "consultor"

    @property
    def disponible(self) -> bool:
        """Un consultor esta disponible siempre (§5-bis.3.6). Un agente de dominio, si esta built."""
        return True if self.es_consultor else self.estado == "built"

    @property
    def habilidades(self) -> list[str]:
        if self.es_consultor:
            return [str(x) for x in (self.registro.get("se_convoca_para") or [])]
        return [str(x) for x in (self.registro.get("outputs") or [])]

    @property
    def no_hace(self) -> list[str]:
        fuente = self.registro.get("no_hace") or self.registro.get("limits") or []
        return [str(x).replace("_", " ") for x in fuente]

    @property
    def convocable_por(self) -> list[str]:
        return [str(x) for x in (self.registro.get("invocable_por") or [])]

    @property
    def herramientas(self) -> list[str]:
        return [str(x) for x in (self.registro.get("tools") or [])]

    @property
    def herramientas_planeadas(self) -> list[str]:
        return [str(x) for x in (self.registro.get("tools_planeadas") or [])]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.agente_id,
            "tipo": self.tipo,
            "nombre": self.nombre,
            "puesto": self.puesto,
            "lema": self.lema,
            "voz": self.voz,
            "mision": self.mision,
            "estado": self.estado,
            "disponible": self.disponible,
            "zona": self.zona,
            "escritorio": self.escritorio,
            "sprite": self.sprite,
            "habilidades": self.habilidades,
            "no_hace": self.no_hace,
            "acciones": self.acciones,
            "herramientas": self.herramientas,
            "herramientas_planeadas": self.herramientas_planeadas,
            "convocable_por": self.convocable_por,
        }


def _cargar(directorio: Path, clave: str) -> dict[str, dict]:
    if not directorio.is_dir():
        return {}
    registros: dict[str, dict] = {}
    for archivo in sorted(directorio.glob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
        registros[str(datos.get(clave) or archivo.stem)] = datos
    return registros


def cargar_identidades() -> dict:
    if not IDENTIDADES.is_file():
        return {"agentes": {}, "zonas": {}}
    return yaml.safe_load(IDENTIDADES.read_text(encoding="utf-8")) or {"agentes": {}, "zonas": {}}


def cargar_perfiles() -> dict[str, Perfil]:
    """Todos los agentes con identidad: los 9 consultores y los D#-## que el registro declare."""
    identidades = cargar_identidades().get("agentes") or {}
    perfiles: dict[str, Perfil] = {}

    for consultor_id, datos in _cargar(DIR_CONSULTORES, "consultant_id").items():
        perfiles[consultor_id] = Perfil(
            agente_id=consultor_id,
            tipo="consultor",
            puesto=str(datos.get("nombre") or consultor_id),
            mision=" ".join(str(x) for x in (datos.get("se_convoca_para") or []))[:400],
            estado="disponible",
            registro=datos,
            identidad=dict(identidades.get(consultor_id) or {}),
        )

    for agente_id, datos in _cargar(DIR_AGENTES, "id").items():
        perfiles[agente_id] = Perfil(
            agente_id=agente_id,
            tipo="dominio",
            puesto=str(datos.get("name") or agente_id),
            mision=str(datos.get("mission") or "").strip(),
            estado=str(datos.get("estado") or "planned"),
            registro=datos,
            identidad=dict(identidades.get(agente_id) or {}),
        )

    return perfiles


def perfil(agente_id: str) -> Perfil:
    perfiles = cargar_perfiles()
    if agente_id not in perfiles:
        raise PerfilDesconocido(f"{agente_id} no esta en registry/agents/ ni en registry/consultants/")
    return perfiles[agente_id]
