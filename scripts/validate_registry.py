"""Validador del registro (arquitectura v3, seccion 10.3).

Las diez reglas de la seccion 10.3, mas dos propias de la Fase 0:

  7b  todo test declarado por un servicio existe de verdad en tests/
  7c  todo servicio `built` tiene modulo Python importable

Las reglas que dependen de piezas que aun no existen (el catalogo de
habilidades, el registro de agentes) se reportan como OMITIDA con el motivo.
Una regla omitida no es una regla en verde: se distingue en la salida para que
nadie confunda "no aplica todavia" con "cumple".

Uso:
    python scripts/validate_registry.py [--raiz .] [--verbose]

Codigo de salida 0 si ninguna regla falla, 1 si alguna falla.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FORMATO_AGENTE = re.compile(r"^D[1-8]-\d{2}$|^O1$")
FORMATO_CONSULTOR = re.compile(r"^C-\d{2}$")
FORMATO_SERVICIO = re.compile(r"^svc-[a-z0-9-]+$")
FORMATO_ACT = re.compile(r"^ACT-[A-Z0-9-]+$")
FORMATO_CTL = re.compile(r"^CTL-[A-Z]+$")


@dataclass
class Resultado:
    numero: str
    descripcion: str
    fallas: list[str] = field(default_factory=list)
    omitida: str = ""

    @property
    def estado(self) -> str:
        if self.omitida:
            return "OMITIDA"
        return "FALLA" if self.fallas else "OK"


@dataclass
class Registro:
    agentes: dict[str, dict]
    consultores: dict[str, dict]
    servicios: dict[str, dict]
    equipos: dict[str, dict]
    raiz: Path
    # El roadmap declara los 33 agentes y los 31 servicios con su fase, tengan archivo o no.
    # Sin el, en cuanto registry/agents/ deja de estar vacio todo owner_digital que apunte a un
    # agente de una fase futura se veria como un error, y no lo es.
    roadmap_agentes: dict[str, dict] = field(default_factory=dict)
    roadmap_servicios: dict[str, dict] = field(default_factory=dict)

    def agente_declarado(self, identificador: str) -> bool:
        return identificador in self.agentes or identificador in self.roadmap_agentes

    def servicio_declarado(self, identificador: str) -> bool:
        return identificador in self.servicios or identificador in self.roadmap_servicios


def cargar_yaml(ruta: Path) -> dict:
    contenido = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    if not isinstance(contenido, dict):
        raise ValueError(f"{ruta}: se esperaba un mapa YAML")
    return contenido


def cargar_registro(raiz: Path) -> Registro:
    def carpeta(nombre: str, clave: str) -> dict[str, dict]:
        directorio = raiz / "registry" / nombre
        if not directorio.is_dir():
            return {}
        indexado: dict[str, dict] = {}
        for archivo in sorted(directorio.glob("*.yaml")):
            datos = cargar_yaml(archivo)
            datos["__archivo__"] = str(archivo.relative_to(raiz)).replace("\\", "/")
            indexado[str(datos.get(clave) or archivo.stem)] = datos
        return indexado

    roadmap_ruta = raiz / "registry" / "policies" / "roadmap.yaml"
    roadmap = cargar_yaml(roadmap_ruta) if roadmap_ruta.is_file() else {}

    return Registro(
        agentes=carpeta("agents", "id"),
        consultores=carpeta("consultants", "consultant_id"),
        servicios=carpeta("services", "id"),
        equipos=carpeta("teams", "team_id"),
        raiz=raiz,
        roadmap_agentes=dict(roadmap.get("agentes") or {}),
        roadmap_servicios=dict(roadmap.get("servicios") or {}),
    )


def _lista(valor) -> list:
    if valor is None:
        return []
    return list(valor) if isinstance(valor, (list, tuple)) else [valor]


def _nombres_de_tests(raiz: Path) -> set[str]:
    nombres: set[str] = set()
    for archivo in (raiz / "tests").rglob("test_*.py"):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.startswith("def test_"):
                nombres.add(linea[4:].split("(")[0].strip())
    return nombres


# --- reglas ---------------------------------------------------------------


def regla_1(reg: Registro) -> Resultado:
    r = Resultado("1", "Toda habilidad referenciada existe en el catalogo")
    if not (reg.raiz / "docs" / "catalogo-habilidades.md").is_file():
        r.omitida = "falta docs/catalogo-habilidades.md (se construye con el primer agente, Fase 1)"
    return r


def regla_2(reg: Registro) -> Resultado:
    r = Resultado("2", "Todo servicio declarado por un agente existe o esta en el roadmap")
    if not reg.agentes:
        r.omitida = "aun no hay agentes en registry/agents/"
        return r
    for agente_id, agente in reg.agentes.items():
        declaradas = _lista(agente.get("tools")) + _lista(agente.get("tools_planeadas"))
        for herramienta in declaradas:
            nombre = str(herramienta)
            if not FORMATO_SERVICIO.match(nombre):
                continue  # herramienta que no es servicio (repo, bitacora del office)
            if not reg.servicio_declarado(nombre):
                r.fallas.append(f"{agente_id} declara {nombre}, que no esta ni construido ni en el roadmap")
        # Un servicio que ya existe construido no tiene por que seguir en la lista de planeadas.
        for planeada in _lista(agente.get("tools_planeadas")):
            servicio = reg.servicios.get(str(planeada))
            if servicio and str(servicio.get("estado")) == "built":
                r.fallas.append(
                    f"{agente_id} lista {planeada} como planeada, pero ya esta built: muevela a tools"
                )
    return r


def regla_3(reg: Registro) -> Resultado:
    r = Resultado("3", "Todo ACT-* tiene al menos un CTL-* asociado")
    if not reg.agentes:
        r.omitida = "aun no hay agentes que declaren ACT-*"
        return r
    for agente_id, agente in reg.agentes.items():
        acciones = [a for a in _lista(agente.get("actions")) if FORMATO_ACT.match(str(a))]
        controles = [c for c in _lista(agente.get("controls")) if FORMATO_CTL.match(str(c))]
        if acciones and not controles:
            r.fallas.append(f"{agente_id} declara {', '.join(acciones)} sin ningun CTL-*")
    return r


def regla_3b(reg: Registro) -> Resultado:
    r = Resultado("3b", "Ningun consultor C-## declara un ACT-*")
    for consultor_id, consultor in reg.consultores.items():
        acciones = _lista(consultor.get("acciones_act")) + _lista(consultor.get("actions"))
        if acciones:
            r.fallas.append(f"{consultor_id} declara acciones {acciones}: un consultor no ejecuta jamas")
    return r


def regla_4(reg: Registro) -> Resultado:
    r = Resultado("4", "Ninguna capacidad del catalogo queda huerfana")
    if not (reg.raiz / "docs" / "catalogo-habilidades.md").is_file():
        r.omitida = "falta docs/catalogo-habilidades.md"
    return r


def regla_5(reg: Registro) -> Resultado:
    r = Resultado("5", "Todo equipo tiene owner humano y owner digital valido")
    for equipo_id, equipo in reg.equipos.items():
        if not str(equipo.get("owner_humano") or "").strip():
            r.fallas.append(f"{equipo_id} sin owner_humano")
        digital = str(equipo.get("owner_digital") or "").strip()
        if not digital:
            r.fallas.append(f"{equipo_id} sin owner_digital")
            continue
        # Seccion 17.4: el owner digital puede ser agente, servicio, consultor o "humano".
        if digital == "humano":
            continue
        if FORMATO_AGENTE.match(digital):
            # Vale que aun no tenga archivo, pero entonces el roadmap tiene que declararlo:
            # asi "todavia no toca" queda escrito y no se confunde con "se nos olvido".
            if not reg.agente_declarado(digital):
                r.fallas.append(
                    f"{equipo_id}: owner_digital {digital} no existe en registry/agents/ "
                    f"ni esta declarado en registry/policies/roadmap.yaml"
                )
        elif FORMATO_SERVICIO.match(digital):
            if digital not in reg.servicios:
                r.fallas.append(f"{equipo_id}: owner_digital {digital} no existe en registry/services/")
        elif FORMATO_CONSULTOR.match(digital):
            if digital not in reg.consultores:
                r.fallas.append(f"{equipo_id}: owner_digital {digital} no existe en registry/consultants/")
        else:
            r.fallas.append(f"{equipo_id}: owner_digital {digital!r} no es agente, servicio, consultor ni 'humano'")
    return r


def regla_6(reg: Registro) -> Resultado:
    r = Resultado("6", "Todo equipo tiene agente asociado o razon explicita de cobertura")
    for equipo_id, equipo in reg.equipos.items():
        if not _lista(equipo.get("agentes")) and not str(equipo.get("razon_cobertura") or "").strip():
            r.fallas.append(f"{equipo_id} sin agentes y sin razon_cobertura: equipo fantasma")
    return r


def regla_7(reg: Registro) -> Resultado:
    r = Resultado("7", "Todo servicio declara al menos un test y al menos un consumidor")
    for servicio_id, servicio in reg.servicios.items():
        if not _lista(servicio.get("tests")):
            r.fallas.append(f"{servicio_id} no declara tests")
        if not _lista(servicio.get("consumidores")):
            r.fallas.append(f"{servicio_id} no declara consumidores")
    return r


def regla_7b(reg: Registro) -> Resultado:
    r = Resultado("7b", "Todo test declarado por un servicio existe en tests/")
    if not (reg.raiz / "tests").is_dir():
        r.omitida = "no hay directorio tests/"
        return r
    existentes = _nombres_de_tests(reg.raiz)
    for servicio_id, servicio in reg.servicios.items():
        for test in _lista(servicio.get("tests")):
            if str(test) not in existentes:
                r.fallas.append(f"{servicio_id} declara {test}, que no existe en tests/")
    return r


def regla_7c(reg: Registro) -> Resultado:
    r = Resultado("7c", "Todo servicio built tiene modulo Python")
    for servicio_id, servicio in reg.servicios.items():
        if str(servicio.get("estado")) != "built":
            continue
        modulo = str(servicio.get("modulo") or "").strip()
        if not modulo:
            r.fallas.append(f"{servicio_id} esta built pero no declara modulo")
        elif not (reg.raiz / modulo).is_dir() and not (reg.raiz / f"{modulo}.py").is_file():
            r.fallas.append(f"{servicio_id} declara modulo {modulo}, que no existe")
    return r


def regla_8(reg: Registro) -> Resultado:
    r = Resultado("8", "Ningun agente built depende de un servicio planned")
    construidos = [a for a in reg.agentes.values() if str(a.get("estado")) == "built"]
    if not construidos:
        r.omitida = "aun no hay agentes built"
        return r
    for agente in construidos:
        for herramienta in _lista(agente.get("tools")):
            servicio = reg.servicios.get(str(herramienta))
            if servicio and str(servicio.get("estado")) != "built":
                r.fallas.append(
                    f"{agente.get('id')} esta built y depende de {herramienta}, que sigue {servicio.get('estado')}"
                )
    return r


def regla_9(reg: Registro) -> Resultado:
    r = Resultado("9", "Todo agente pertenece a un departamento y a equipos existentes")
    if not reg.agentes:
        r.omitida = "aun no hay agentes"
        return r
    nombres_equipo = {str(e.get("nombre", "")).strip().lower() for e in reg.equipos.values()}
    ids_equipo = set(reg.equipos)
    for agente_id, agente in reg.agentes.items():
        if not str(agente.get("department") or "").strip():
            r.fallas.append(f"{agente_id} sin departamento")
        equipos = _lista(agente.get("teams"))
        if not equipos:
            r.fallas.append(f"{agente_id} sin equipos")
        for equipo in equipos:
            clave = str(equipo).strip()
            if clave in ids_equipo:
                continue
            if clave.replace("-", " ").lower() in nombres_equipo:
                continue
            r.fallas.append(f"{agente_id} declara el equipo {clave!r}, que no esta en registry/teams/")
    return r


def regla_10(reg: Registro) -> Resultado:
    r = Resultado("10", "Todo agente declara model_tier y todo servicio declara fase")
    for agente_id, agente in reg.agentes.items():
        if not str(agente.get("model_tier") or "").strip():
            r.fallas.append(f"{agente_id} sin model_tier")
    for servicio_id, servicio in reg.servicios.items():
        if servicio.get("fase") is None:
            r.fallas.append(f"{servicio_id} sin fase")
        if not str(servicio.get("estado") or "").strip():
            r.fallas.append(f"{servicio_id} sin estado")
    return r


def regla_11(reg: Registro) -> Resultado:
    """Propia de este repo: el roadmap y el registro tienen que contarse la misma historia."""
    r = Resultado("11", "Registro y roadmap coinciden en cobertura y fase")
    if not reg.roadmap_agentes and not reg.roadmap_servicios:
        r.omitida = "falta registry/policies/roadmap.yaml"
        return r

    for agente_id, agente in reg.agentes.items():
        declarado = reg.roadmap_agentes.get(agente_id)
        if declarado is None:
            r.fallas.append(f"{agente_id} tiene archivo pero no esta en el roadmap")
        elif agente.get("fase") is not None and agente.get("fase") != declarado.get("fase"):
            r.fallas.append(
                f"{agente_id} declara fase {agente.get('fase')} y el roadmap dice {declarado.get('fase')}"
            )

    for servicio_id, servicio in reg.servicios.items():
        declarado = reg.roadmap_servicios.get(servicio_id)
        if declarado is None:
            r.fallas.append(f"{servicio_id} tiene archivo pero no esta en el roadmap")
        elif servicio.get("fase") != declarado.get("fase"):
            r.fallas.append(
                f"{servicio_id} declara fase {servicio.get('fase')} y el roadmap dice {declarado.get('fase')}"
            )

    # Los consultores estan fuera del roadmap por diseno (§5-bis.3, regla 6): ninguna fase los
    # enciende. Si alguno apareciera en la lista de agentes, seria un error de modelado.
    for consultor_id in reg.consultores:
        if consultor_id in reg.roadmap_agentes:
            r.fallas.append(f"{consultor_id} es consultor y no debe tener fase en el roadmap")

    return r


def regla_12(reg: Registro) -> Resultado:
    """Adelantar un agente es una decision, y las decisiones se escriben."""
    r = Resultado("12", "Todo agente construido antes de su fase declara por que")
    construidos = {aid: a for aid, a in reg.agentes.items() if str(a.get("estado")) == "built"}
    if not construidos:
        r.omitida = "aun no hay agentes built"
        return r
    for agente_id, agente in construidos.items():
        adelantado = agente.get("adelantado_a")
        if adelantado is None:
            continue
        if not str(agente.get("razon_adelanto") or "").strip():
            r.fallas.append(f"{agente_id} se adelanto a la fase {adelantado} sin razon_adelanto")
        if agente.get("fase") is not None and adelantado >= agente.get("fase"):
            r.fallas.append(
                f"{agente_id} declara adelantado_a {adelantado}, que no adelanta nada sobre su fase "
                f"{agente.get('fase')}"
            )
        if _lista(agente.get("actions")):
            r.fallas.append(
                f"{agente_id} esta adelantado y ademas declara ACT-*: un agente fuera de fase no ejecuta"
            )
    return r


REGLAS = (
    regla_1,
    regla_2,
    regla_3,
    regla_3b,
    regla_4,
    regla_5,
    regla_6,
    regla_7,
    regla_7b,
    regla_7c,
    regla_8,
    regla_9,
    regla_10,
    regla_11,
    regla_12,
)


def validar(raiz: Path) -> list[Resultado]:
    registro = cargar_registro(raiz)
    return [regla(registro) for regla in REGLAS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida registry/ contra la seccion 10.3 de la arquitectura v3.")
    parser.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--verbose", action="store_true", help="lista las reglas omitidas con su motivo")
    args = parser.parse_args(argv)

    raiz = Path(args.raiz)
    resultados = validar(raiz)
    registro = cargar_registro(raiz)

    print(
        f"registry: {len(registro.agentes)} agentes, {len(registro.servicios)} servicios, "
        f"{len(registro.consultores)} consultores, {len(registro.equipos)} equipos"
    )
    print("-" * 78)
    for resultado in resultados:
        print(f"[{resultado.estado:^7}] regla {resultado.numero:<3} {resultado.descripcion}")
        for falla in resultado.fallas:
            print(f"            - {falla}")
        if resultado.omitida and args.verbose:
            print(f"            motivo: {resultado.omitida}")

    fallidas = [r for r in resultados if r.fallas]
    omitidas = [r for r in resultados if r.omitida]
    print("-" * 78)
    print(
        f"{len(resultados) - len(fallidas) - len(omitidas)} en verde, "
        f"{len(fallidas)} en falla, {len(omitidas)} omitidas"
    )
    return 1 if fallidas else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
