"""Memoria persistente por agente.

Un archivo Markdown por agente, versionado en git. Esa es toda la tecnologia, y es a
proposito: la memoria de un agente tiene que poder leerse, corregirse a mano y revisarse en un
diff. Una memoria que solo el sistema puede leer es una memoria que nadie audita.

Formato:

    # Memoria - Renata (C-01) - Producto y UX
    ## Habilidades
    - Flujos de pantalla y wireframes
    ## Notas
    ### 2026-08-18 - E-004 - decision
    La bandeja HITL ordena por SLA vencido primero, no por fecha de creacion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO = RAIZ / "agents" / "memoria"

TIPOS = ("decision", "supuesto", "trampa", "aprendizaje", "contexto")
ENCABEZADO_NOTA = re.compile(r"^###\s+(\S+)\s+-\s+(\S+)\s+-\s+(\w+)\s*$")


@dataclass(frozen=True)
class Nota:
    fecha: str
    encargo: str
    tipo: str
    texto: str

    def as_dict(self) -> dict[str, str]:
        return {"fecha": self.fecha, "encargo": self.encargo, "tipo": self.tipo, "texto": self.texto}


@dataclass
class Memoria:
    agente_id: str
    habilidades: list[str] = field(default_factory=list)
    notas: list[Nota] = field(default_factory=list)

    @property
    def existe(self) -> bool:
        return ruta(self.agente_id).is_file()

    def recientes(self, cuantas: int = 5) -> list[Nota]:
        return self.notas[-cuantas:][::-1]

    def as_dict(self) -> dict[str, object]:
        return {
            "agente_id": self.agente_id,
            "habilidades": self.habilidades,
            "notas": [n.as_dict() for n in self.notas],
        }


def ruta(agente_id: str) -> Path:
    return DIRECTORIO / f"{agente_id}.md"


def crear(agente_id: str, titulo: str, habilidades: list[str]) -> Path:
    """Crea el archivo de memoria si no existe. Nunca sobreescribe: la memoria no se reinicia."""
    destino = ruta(agente_id)
    if destino.is_file():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    lineas = [f"# Memoria - {titulo}", "", "## Habilidades", ""]
    lineas += [f"- {h}" for h in habilidades] or ["- (sin habilidades declaradas)"]
    lineas += ["", "## Notas", ""]
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def leer(agente_id: str) -> Memoria:
    destino = ruta(agente_id)
    memoria = Memoria(agente_id=agente_id)
    if not destino.is_file():
        return memoria

    seccion = ""
    nota_actual: dict[str, object] | None = None
    for linea in destino.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            if nota_actual:
                memoria.notas.append(_cerrar(nota_actual))
                nota_actual = None
            seccion = linea[3:].strip().lower()
            continue

        if seccion == "habilidades" and linea.startswith("- "):
            memoria.habilidades.append(linea[2:].strip())
            continue

        if seccion == "notas":
            encabezado = ENCABEZADO_NOTA.match(linea)
            if encabezado:
                if nota_actual:
                    memoria.notas.append(_cerrar(nota_actual))
                fecha_nota, encargo, tipo = encabezado.groups()
                nota_actual = {"fecha": fecha_nota, "encargo": encargo, "tipo": tipo, "lineas": []}
            elif nota_actual is not None and linea.strip():
                nota_actual["lineas"].append(linea.strip())

    if nota_actual:
        memoria.notas.append(_cerrar(nota_actual))
    return memoria


def _cerrar(nota: dict[str, object]) -> Nota:
    return Nota(
        fecha=str(nota["fecha"]),
        encargo=str(nota["encargo"]),
        tipo=str(nota["tipo"]),
        texto=" ".join(nota["lineas"]).strip(),  # type: ignore[arg-type]
    )


def anotar(
    agente_id: str,
    texto: str,
    *,
    tipo: str = "aprendizaje",
    encargo: str = "-",
    cuando: date | None = None,
) -> Nota:
    """Agrega una nota al final. Append-only: corregir una nota vieja es escribir una nueva."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo de nota desconocido: {tipo!r}; validos: {', '.join(TIPOS)}")
    texto_limpio = " ".join(texto.split())
    if not texto_limpio:
        raise ValueError("una nota vacia no es memoria")

    destino = ruta(agente_id)
    if not destino.is_file():
        crear(agente_id, agente_id, [])

    nota = Nota(fecha=(cuando or date.today()).isoformat(), encargo=encargo or "-", tipo=tipo, texto=texto_limpio)
    with destino.open("a", encoding="utf-8") as archivo:
        archivo.write(f"\n### {nota.fecha} - {nota.encargo} - {nota.tipo}\n{nota.texto}\n")
    return nota
