"""svc-trace - trazabilidad de cifras (§8).

Responde una sola pregunta: **¿de dónde salió este número?** Y hace algo más útil que
responderla: **bloquea el entregable que no la puede responder.**

El mecanismo tiene dos mitades:

1. Todo servicio que produce una cifra la **registra** con su origen, su versión y su consulta.
2. Antes de entregar, se **reconcilia** el entregable contra el libro: cada cifra citada tiene
   que existir, coincidir al centavo, y ningún número suelto puede aparecer en la prosa sin
   estar respaldado.

La segunda mitad es la que atrapa la alucinación. Un agente que redacta "el margen ronda el 22%"
sobre un margen registrado de 16% no falla por mala fe: falla porque redondear hacia arriba suena
mejor. Aquí no pasa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from services.common.errors import ErrorDeServicio
from services.common.money import cantidad


class EntregableNoCuadra(ErrorDeServicio):
    """Una cifra del entregable no se puede reconciliar con su origen."""

    codigo = "TRACE-NO-CUADRA"


@dataclass(frozen=True)
class Cifra:
    """Un número con su procedencia. Sin procedencia no es una cifra: es una opinión."""

    cifra_id: str
    nombre: str
    valor: Decimal
    servicio: str
    consulta: str
    version: str = "v1"
    trace_id: str = ""
    generada: str = ""
    unidad: str = "MXN"

    def as_dict(self) -> dict[str, object]:
        return {
            "cifra_id": self.cifra_id,
            "nombre": self.nombre,
            "valor": str(self.valor),
            "servicio": self.servicio,
            "consulta": self.consulta,
            "version": self.version,
            "trace_id": self.trace_id,
            "generada": self.generada,
            "unidad": self.unidad,
        }


@dataclass
class Libro:
    """Las cifras vivas de un caso. Un libro por trace: las cifras no cruzan de caso."""

    trace_id: str = ""
    cifras: dict[str, Cifra] = field(default_factory=dict)

    def registrar(
        self,
        nombre: str,
        valor: object,
        *,
        servicio: str,
        consulta: str,
        version: str = "v1",
        unidad: str = "MXN",
        cifra_id: str | None = None,
    ) -> Cifra:
        identificador = cifra_id or f"CF-{len(self.cifras) + 1:03d}"
        if identificador in self.cifras:
            raise ErrorDeServicio(f"cifra duplicada: {identificador}", campo="cifra_id")
        cifra = Cifra(
            cifra_id=identificador,
            nombre=nombre,
            valor=cantidad(valor, campo=nombre),
            servicio=servicio,
            consulta=consulta,
            version=version,
            trace_id=self.trace_id,
            generada=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            unidad=unidad,
        )
        self.cifras[identificador] = cifra
        return cifra

    def por_nombre(self, nombre: str) -> Cifra | None:
        return next((c for c in self.cifras.values() if c.nombre == nombre), None)

    def as_dict(self) -> dict[str, object]:
        return {"trace_id": self.trace_id, "cifras": [c.as_dict() for c in self.cifras.values()]}


# --- reconciliación -------------------------------------------------------

# Números que aparecen en prosa: 26,500.00 · $18,200 · 22.4% · 930
NUMERO = re.compile(r"(?<![\w.])\$?\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s?%?")

# Cifras que no vale la pena perseguir: años, cantidades de un dígito, porcentajes redondos
# de uso común en prosa ("los 3 meses de fondo"). El filtro es explícito para poder discutirlo.
TOLERADOS = {Decimal(x) for x in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "100")}


@dataclass(frozen=True)
class Discrepancia:
    clave: str
    citado: str
    registrado: str
    cifra_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "clave": self.clave,
            "citado": self.citado,
            "registrado": self.registrado,
            "cifra_id": self.cifra_id,
        }


@dataclass
class Reconciliacion:
    trace_id: str
    discrepancias: list[Discrepancia] = field(default_factory=list)
    sin_fuente: list[str] = field(default_factory=list)
    fuente_inexistente: list[str] = field(default_factory=list)
    numeros_sueltos: list[str] = field(default_factory=list)
    verificadas: int = 0

    @property
    def ok(self) -> bool:
        return not (self.discrepancias or self.sin_fuente or self.fuente_inexistente or self.numeros_sueltos)

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "ok": self.ok,
            "verificadas": self.verificadas,
            "discrepancias": [d.as_dict() for d in self.discrepancias],
            "sin_fuente": self.sin_fuente,
            "fuente_inexistente": self.fuente_inexistente,
            "numeros_sueltos": self.numeros_sueltos,
        }

    def resumen(self) -> str:
        if self.ok:
            return f"{self.verificadas} cifra(s) reconciliadas contra su origen"
        partes = []
        if self.discrepancias:
            partes.append(f"{len(self.discrepancias)} no coinciden con el origen")
        if self.sin_fuente:
            partes.append(f"{len(self.sin_fuente)} sin fuente declarada")
        if self.fuente_inexistente:
            partes.append(f"{len(self.fuente_inexistente)} citan una fuente que no existe")
        if self.numeros_sueltos:
            partes.append(f"{len(self.numeros_sueltos)} número(s) en el texto sin respaldo")
        return "; ".join(partes)


def numeros_en_texto(texto: str) -> list[Decimal]:
    """Extrae los números de la prosa, ya normalizados."""
    encontrados: list[Decimal] = []
    for bruto in NUMERO.findall(texto or ""):
        try:
            encontrados.append(cantidad(bruto))
        except (ErrorDeServicio, InvalidOperation):
            continue
    return encontrados


def reconciliar(entregable: dict, libro: Libro, *, revisar_texto: bool = True) -> Reconciliacion:
    """Verifica el entregable contra el libro de cifras.

    `cifras` son los números que el entregable afirma; `fuentes` los liga a una cifra del libro.
    Con `revisar_texto`, además busca números en la prosa que no correspondan a ninguna cifra
    declarada — que es donde se esconde el número inventado.
    """
    reconciliacion = Reconciliacion(trace_id=libro.trace_id)
    cifras = entregable.get("cifras") or {}
    fuentes = entregable.get("fuentes") or {}

    for clave, valor_citado in cifras.items():
        cifra_id = fuentes.get(clave)
        if not cifra_id:
            reconciliacion.sin_fuente.append(clave)
            continue
        registrada = libro.cifras.get(str(cifra_id))
        if registrada is None:
            reconciliacion.fuente_inexistente.append(f"{clave} -> {cifra_id}")
            continue
        if cantidad(valor_citado, campo=clave) != registrada.valor:
            reconciliacion.discrepancias.append(
                Discrepancia(
                    clave=clave,
                    citado=str(cantidad(valor_citado, campo=clave)),
                    registrado=str(registrada.valor),
                    cifra_id=registrada.cifra_id,
                )
            )
            continue
        reconciliacion.verificadas += 1

    if revisar_texto:
        declarados = {cantidad(v) for v in cifras.values()} | {c.valor for c in libro.cifras.values()}
        # Los enteros de una cifra registrada también valen redondeados: "930 km" contra 930.00.
        declarados |= {valor.quantize(Decimal("1")) for valor in set(declarados)}
        for campo in ("resumen", "cuerpo", "texto", "propuesta"):
            for numero in numeros_en_texto(str(entregable.get(campo) or "")):
                if numero in declarados or numero in TOLERADOS:
                    continue
                reconciliacion.numeros_sueltos.append(f"{campo}: {numero}")

    return reconciliacion


def exigir_reconciliacion(entregable: dict, libro: Libro, *, revisar_texto: bool = True) -> Reconciliacion:
    """Reconcilia y bloquea si no cuadra. Es la puerta previa a la entrega."""
    resultado = reconciliar(entregable, libro, revisar_texto=revisar_texto)
    if not resultado.ok:
        raise EntregableNoCuadra(
            f"el entregable no cuadra con su origen: {resultado.resumen()}",
            campo="cifras",
            detalle=resultado.as_dict(),
        )
    return resultado
