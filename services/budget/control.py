"""svc-budget - presupuesto de modelo por agente (§11.5).

Tres reglas:

1. **El tope es por agente y por mes.** Un tope global esconde al agente caro detrás del barato.
2. **Al 80% avisa; al 100% detiene.** Un presupuesto que sólo avisa lo ignora todo el mundo a
   la tercera vez.
3. **El consumo lo provee svc-runlog, no este servicio.** Aquí no se mide nada: se compara lo
   medido contra lo autorizado. Dos fuentes para el mismo número serían dos números.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from services.common.errors import ErrorDeServicio, ErrorDeValidacion
from services.common.money import cantidad, mxn

RAIZ = Path(__file__).resolve().parent.parent.parent
POLITICA = RAIZ / "registry" / "policies" / "budget.yaml"

NIVELES = ("Alto", "Medio", "Bajo")


class PresupuestoExcedido(ErrorDeServicio):
    """El agente agotó su tope del mes. La siguiente llamada la autoriza una persona."""

    codigo = "BUDGET-EXCEDIDO"


@dataclass(frozen=True)
class Politica:
    alerta_pct: Decimal
    corte: str
    costo_por_mil_tokens: dict[str, Decimal]
    tope_por_nivel: dict[str, Decimal]
    tope_por_agente: dict[str, Decimal]
    calibrado: bool = False
    version: str = "v1"

    def tope(self, agente: str, nivel: str = "Medio") -> Decimal:
        if agente in self.tope_por_agente:
            return self.tope_por_agente[agente]
        if nivel not in self.tope_por_nivel:
            raise ErrorDeValidacion(f"nivel de modelo desconocido: {nivel!r}", campo="nivel")
        return self.tope_por_nivel[nivel]

    def costo_estimado(self, tokens: int, nivel: str = "Medio") -> Decimal:
        if nivel not in self.costo_por_mil_tokens:
            raise ErrorDeValidacion(f"nivel de modelo desconocido: {nivel!r}", campo="nivel")
        return mxn(Decimal(tokens) / 1000 * self.costo_por_mil_tokens[nivel])


def cargar_politica(ruta: str | Path | None = None) -> Politica:
    destino = Path(ruta) if ruta else POLITICA
    if not destino.is_file():
        raise ErrorDeServicio(f"no existe la politica de presupuesto: {destino}", campo="politica")
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    return Politica(
        alerta_pct=cantidad(datos.get("alerta_pct", 80), campo="alerta_pct"),
        corte=str(datos.get("corte") or "duro"),
        costo_por_mil_tokens={k: cantidad(v) for k, v in (datos.get("costo_por_mil_tokens") or {}).items()},
        tope_por_nivel={k: mxn(v) for k, v in (datos.get("tope_mensual_por_nivel") or {}).items()},
        tope_por_agente={k: mxn(v) for k, v in (datos.get("tope_mensual_por_agente") or {}).items()},
        calibrado=bool(datos.get("calibrado")),
        version=str(datos.get("version") or "v1"),
    )


@dataclass(frozen=True)
class EstadoPresupuesto:
    agente: str
    periodo: str
    consumido_mxn: Decimal
    tope_mxn: Decimal
    consumido_pct: Decimal
    en_alerta: bool
    excedido: bool
    disponible_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "agente": self.agente,
            "periodo": self.periodo,
            "consumido_mxn": str(self.consumido_mxn),
            "tope_mxn": str(self.tope_mxn),
            "consumido_pct": str(self.consumido_pct),
            "en_alerta": self.en_alerta,
            "excedido": self.excedido,
            "disponible_mxn": str(self.disponible_mxn),
        }


def evaluar(
    agente: str,
    consumido: object,
    *,
    periodo: str,
    nivel: str = "Medio",
    politica: Politica | None = None,
) -> EstadoPresupuesto:
    """Compara lo consumido contra el tope. El consumo viene de svc-runlog."""
    politica = politica or cargar_politica()
    tope = politica.tope(agente, nivel)
    gastado = mxn(consumido, campo="consumido")
    if gastado < 0:
        raise ErrorDeValidacion("el consumo no puede ser negativo", campo="consumido")

    porcentaje = (gastado / tope * 100).quantize(Decimal("0.01")) if tope else Decimal("0.00")
    return EstadoPresupuesto(
        agente=agente,
        periodo=periodo,
        consumido_mxn=gastado,
        tope_mxn=tope,
        consumido_pct=porcentaje,
        en_alerta=porcentaje >= politica.alerta_pct,
        excedido=gastado >= tope,
        disponible_mxn=mxn(max(tope - gastado, Decimal(0))),
    )


@dataclass(frozen=True)
class Autorizacion:
    permitida: bool
    motivo: str
    estado: EstadoPresupuesto
    costo_estimado_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "permitida": self.permitida,
            "motivo": self.motivo,
            "costo_estimado_mxn": str(self.costo_estimado_mxn),
            "estado": self.estado.as_dict(),
        }


def autorizar(
    agente: str,
    *,
    tokens_estimados: int,
    consumido: object,
    periodo: str,
    nivel: str = "Medio",
    politica: Politica | None = None,
) -> Autorizacion:
    """¿Se puede hacer esta llamada? Se pregunta antes, no después de gastar."""
    politica = politica or cargar_politica()
    estado = evaluar(agente, consumido, periodo=periodo, nivel=nivel, politica=politica)
    costo = politica.costo_estimado(tokens_estimados, nivel)

    if estado.excedido:
        return Autorizacion(
            permitida=False,
            motivo=f"{agente} agoto su tope de {estado.tope_mxn} del periodo {periodo}",
            estado=estado,
            costo_estimado_mxn=costo,
        )
    if costo > estado.disponible_mxn:
        return Autorizacion(
            permitida=False,
            motivo=(
                f"la llamada costaria {costo} y a {agente} le quedan {estado.disponible_mxn} "
                f"del periodo {periodo}"
            ),
            estado=estado,
            costo_estimado_mxn=costo,
        )
    motivo = "dentro de presupuesto"
    if estado.en_alerta:
        motivo = f"permitida, pero {agente} va en {estado.consumido_pct}% de su tope"
    return Autorizacion(permitida=True, motivo=motivo, estado=estado, costo_estimado_mxn=costo)


def exigir(
    agente: str,
    *,
    tokens_estimados: int,
    consumido: object,
    periodo: str,
    nivel: str = "Medio",
    politica: Politica | None = None,
) -> Autorizacion:
    """Autoriza o detiene. El corte es duro: §11.5 no contempla pasarse 'un poquito'."""
    decision = autorizar(
        agente, tokens_estimados=tokens_estimados, consumido=consumido, periodo=periodo, nivel=nivel, politica=politica
    )
    if not decision.permitida:
        raise PresupuestoExcedido(decision.motivo, campo="presupuesto", estado=decision.estado.as_dict())
    return decision


def panorama(
    consumo_por_actor: dict[str, dict[str, object]],
    *,
    periodo: str,
    niveles: dict[str, str] | None = None,
    politica: Politica | None = None,
) -> list[EstadoPresupuesto]:
    """Estado de todos los agentes que consumieron, del más apretado al más holgado."""
    politica = politica or cargar_politica()
    niveles = niveles or {}
    estados = [
        evaluar(
            actor,
            fila.get("costo_mxn", 0),
            periodo=periodo,
            nivel=niveles.get(actor, "Medio"),
            politica=politica,
        )
        for actor, fila in consumo_por_actor.items()
        # Los servicios deterministicos cuestan cero y no tienen tope: no ensucian el panorama.
        if not actor.startswith("svc-")
    ]
    return sorted(estados, key=lambda e: e.consumido_pct, reverse=True)
