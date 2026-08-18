"""svc-validation - QA transversal por reglas determinísticas.

El §7.1 dice que `svc-validation` **rechaza el entregable si falta alguno** de los seis campos
del contrato. Esto es esa función, y su forma importa: reglas nombradas, con código estable y
severidad, no un `if` disperso por el código de cada agente.

Un LLM aquí sólo añadiría riesgo. Las reglas son de dominio y son verificables; lo que no es
verificable con una regla —si el texto es *bueno*— no vive aquí: eso lo mira D5-03 sobre
muestra, con rúbrica (§9.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Iterable

from services.common.errors import ErrorDeServicio
from services.common.money import cantidad

SEVERIDADES = ("error", "advertencia")

# Los seis campos del contrato de entregable (§7.1).
CAMPOS_ENTREGABLE = (
    "decision_solicitada",
    "fuentes",
    "supuestos",
    "confianza",
    "opciones",
    "si_no_respondes",
)

NIVELES_CONFIANZA = ("alta", "media", "baja")


class EntregableRechazado(ErrorDeServicio):
    """El objeto no cumple una regla dura. No se entrega."""

    codigo = "VAL-RECHAZADO"


@dataclass(frozen=True)
class Hallazgo:
    regla: str
    campo: str
    mensaje: str
    severidad: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {"regla": self.regla, "campo": self.campo, "mensaje": self.mensaje, "severidad": self.severidad}

    def __str__(self) -> str:  # pragma: no cover - formato
        return f"[{self.regla}] {self.campo}: {self.mensaje}"


@dataclass
class Dictamen:
    ambito: str
    hallazgos: list[Hallazgo] = field(default_factory=list)

    @property
    def errores(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad == "error"]

    @property
    def advertencias(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad == "advertencia"]

    @property
    def ok(self) -> bool:
        return not self.errores

    def as_dict(self) -> dict[str, object]:
        return {
            "ambito": self.ambito,
            "ok": self.ok,
            "errores": [h.as_dict() for h in self.errores],
            "advertencias": [h.as_dict() for h in self.advertencias],
        }


@dataclass(frozen=True)
class Regla:
    codigo: str
    ambito: str
    descripcion: str
    funcion: Callable[[dict], Iterable[Hallazgo]]


CATALOGO: dict[str, list[Regla]] = {}


def registrar(regla: Regla) -> Regla:
    """Da de alta una regla. Otros servicios registran las suyas sin tocar este archivo."""
    if regla.codigo in {r.codigo for reglas in CATALOGO.values() for r in reglas}:
        raise ErrorDeServicio(f"regla duplicada: {regla.codigo}", campo="codigo")
    CATALOGO.setdefault(regla.ambito, []).append(regla)
    return regla


def regla(codigo: str, ambito: str, descripcion: str):
    """Decorador para declarar una regla junto a su lógica."""

    def envoltura(funcion: Callable[[dict], Iterable[Hallazgo]]) -> Callable[[dict], Iterable[Hallazgo]]:
        registrar(Regla(codigo=codigo, ambito=ambito, descripcion=descripcion, funcion=funcion))
        return funcion

    return envoltura


def validar(objeto: dict, ambito: str) -> Dictamen:
    """Aplica todas las reglas del ámbito. Devuelve todos los hallazgos, no sólo el primero."""
    if ambito not in CATALOGO:
        raise ErrorDeServicio(
            f"ambito sin reglas: {ambito!r}; conocidos: {', '.join(sorted(CATALOGO))}", campo="ambito"
        )
    dictamen = Dictamen(ambito=ambito)
    for r in CATALOGO[ambito]:
        dictamen.hallazgos.extend(r.funcion(objeto))
    return dictamen


def exigir(objeto: dict, ambito: str) -> Dictamen:
    """Valida y levanta si hay errores. Es la puerta por la que pasa todo entregable."""
    dictamen = validar(objeto, ambito)
    if not dictamen.ok:
        detalle = "; ".join(str(h) for h in dictamen.errores)
        raise EntregableRechazado(
            f"{len(dictamen.errores)} regla(s) incumplida(s) en {ambito}: {detalle}",
            campo=ambito,
            hallazgos=[h.as_dict() for h in dictamen.errores],
        )
    return dictamen


def _vacio(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, tuple, dict, set)):
        return len(valor) == 0
    return False


# --- ámbito: entregable (§7.1) -------------------------------------------


@regla("VAL-ENT-001", "entregable", "Los seis campos del contrato están presentes y no vacíos")
def _campos_del_contrato(entregable: dict) -> list[Hallazgo]:
    return [
        Hallazgo("VAL-ENT-001", campo, "campo obligatorio del contrato de entregable, vacío o ausente")
        for campo in CAMPOS_ENTREGABLE
        if _vacio(entregable.get(campo))
    ]


@regla("VAL-ENT-002", "entregable", "Una decisión solicitada llega con al menos dos opciones")
def _opciones_reales(entregable: dict) -> list[Hallazgo]:
    decision = str(entregable.get("decision_solicitada") or "").strip().lower()
    if not decision or decision.startswith("ninguna"):
        return []
    opciones = entregable.get("opciones") or []
    if len(opciones) >= 2 or str(entregable.get("opcion_unica_justificada") or "").strip():
        return []
    # §7.1: "no una recomendación única disfrazada de conclusión".
    return [
        Hallazgo(
            "VAL-ENT-002",
            "opciones",
            "se pide decidir pero llega una sola opción y sin justificar por qué no hay alternativa",
        )
    ]


@regla("VAL-ENT-003", "entregable", "La confianza declara nivel y qué la limita")
def _confianza(entregable: dict) -> list[Hallazgo]:
    confianza = entregable.get("confianza")
    if _vacio(confianza):
        return []  # ya lo reporta VAL-ENT-001
    if isinstance(confianza, str):
        return [Hallazgo("VAL-ENT-003", "confianza", "declara nivel pero no qué lo limita")]
    nivel = str(confianza.get("nivel") or "").lower()
    hallazgos = []
    if nivel not in NIVELES_CONFIANZA:
        hallazgos.append(
            Hallazgo("VAL-ENT-003", "confianza.nivel", f"nivel desconocido: {nivel!r}; use alta, media o baja")
        )
    if _vacio(confianza.get("limitado_por")):
        hallazgos.append(Hallazgo("VAL-ENT-003", "confianza.limitado_por", "falta qué limita la confianza"))
    return hallazgos


@regla("VAL-ENT-004", "entregable", "Cada cifra citada declara su fuente")
def _cifras_con_fuente(entregable: dict) -> list[Hallazgo]:
    cifras = entregable.get("cifras") or {}
    fuentes = entregable.get("fuentes") or {}
    if not isinstance(cifras, dict) or not isinstance(fuentes, dict):
        return [Hallazgo("VAL-ENT-004", "cifras", "cifras y fuentes deben ser mapas clave -> valor")]
    return [
        Hallazgo("VAL-ENT-004", f"fuentes.{clave}", "cifra citada sin fuente declarada")
        for clave in cifras
        if clave not in fuentes
    ]


@regla("VAL-ENT-005", "entregable", "El plazo de si_no_respondes es concreto")
def _plazo_concreto(entregable: dict) -> list[Hallazgo]:
    texto = str(entregable.get("si_no_respondes") or "")
    if _vacio(texto):
        return []
    tiene_plazo = any(palabra in texto.lower() for palabra in ("hora", "día", "dia", "semana", "hábil", "habil"))
    if tiene_plazo:
        return []
    # §7.1 pide "qué ocurre... y en cuánto tiempo". Sin tiempo, no es un aviso: es una frase.
    return [Hallazgo("VAL-ENT-005", "si_no_respondes", "no dice en cuánto tiempo", severidad="advertencia")]


# --- ámbito: cotización ---------------------------------------------------


@regla("VAL-COT-001", "cotizacion", "El margen alcanza el mínimo de la ruta")
def _margen_minimo(cotizacion: dict) -> list[Hallazgo]:
    minimo = cotizacion.get("margen_minimo_pct")
    margen = cotizacion.get("margen_pct")
    if minimo is None or margen is None:
        return [Hallazgo("VAL-COT-001", "margen_pct", "falta el margen o el mínimo de la ruta")]
    if cantidad(margen) < cantidad(minimo):
        return [
            Hallazgo(
                "VAL-COT-001",
                "margen_pct",
                f"margen {margen}% por debajo del mínimo {minimo}% de la ruta: requiere Dirección",
            )
        ]
    return []


@regla("VAL-COT-002", "cotizacion", "El descuento respeta el umbral del Gate")
def _descuento(cotizacion: dict) -> list[Hallazgo]:
    descuento = cotizacion.get("descuento_pct")
    if descuento is None:
        return []
    tope = cotizacion.get("descuento_max_pct")
    if tope is None:
        return [Hallazgo("VAL-COT-002", "descuento_max_pct", "hay descuento pero no hay umbral contra el cual medirlo")]
    if cantidad(descuento) > cantidad(tope):
        return [
            Hallazgo(
                "VAL-COT-002",
                "descuento_pct",
                f"descuento {descuento}% por encima del umbral {tope}%: lo autoriza Dirección",
            )
        ]
    return []


@regla("VAL-COT-003", "cotizacion", "El precio cubre el costo")
def _precio_cubre_costo(cotizacion: dict) -> list[Hallazgo]:
    precio = cotizacion.get("precio_mxn")
    costo = cotizacion.get("costo_mxn")
    if precio is None or costo is None:
        return []
    if cantidad(precio) <= cantidad(costo):
        return [Hallazgo("VAL-COT-003", "precio_mxn", f"el precio {precio} no cubre el costo {costo}")]
    return []


# --- ámbito: costeo -------------------------------------------------------


@regla("VAL-CST-001", "costeo", "El desglose suma el total y el costo por km es positivo")
def _costeo_coherente(costeo: dict) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    desglose = costeo.get("desglose") or {}
    variable = costeo.get("variable_cost")
    fijos = costeo.get("fixed_allocated_cost")
    total = costeo.get("total_trip_cost")

    if desglose and variable is not None:
        suma = sum((cantidad(v) for v in desglose.values()), Decimal(0))
        if suma != cantidad(variable):
            hallazgos.append(
                Hallazgo("VAL-CST-001", "desglose", f"el desglose suma {suma} y el costo variable dice {variable}")
            )
    if None not in (variable, fijos, total) and cantidad(variable) + cantidad(fijos) != cantidad(total):
        hallazgos.append(Hallazgo("VAL-CST-001", "total_trip_cost", "variable + fijos no da el total"))
    if costeo.get("cost_per_km") is not None and cantidad(costeo["cost_per_km"]) <= 0:
        hallazgos.append(Hallazgo("VAL-CST-001", "cost_per_km", "costo por km no positivo"))
    return hallazgos


@regla("VAL-CST-002", "costeo", "Los supuestos vienen declarados")
def _supuestos_declarados(costeo: dict) -> list[Hallazgo]:
    if "assumptions" not in costeo:
        return [Hallazgo("VAL-CST-002", "assumptions", "el costeo no declara supuestos")]
    return []
