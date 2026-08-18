"""svc-profitability - margen por viaje, ruta, cliente, unidad y operador.

El segundo entregable de la Fase 0 y el que cambia decisiones: no cuanto se
factura, sino cuanto queda. Consume el costo de svc-costing; no lo recalcula.

Aqui tambien vive la distribucion de margen real, que es el insumo del
procedimiento de calibracion de docs/umbrales.md: el margen objetivo y el
minimo por ruta se proponen sobre esta distribucion, no sobre un supuesto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Iterable, Sequence

from services.common.errors import ErrorDeValidacion
from services.common.money import cuota, mxn
from services.costing.motor import ResultadoCosteo
from services.ingest.registros import Viaje
from services.masterdata.catalogo import Catalogo

DOS = Decimal("0.01")


@dataclass(frozen=True)
class MargenViaje:
    """Margen de un viaje cerrado. Unidad minima de todo lo que sigue."""

    trip_id: str
    route_id: str
    cliente_id: str
    unit_id: str
    operador_id: str
    fecha: date
    km: Decimal
    ingreso_mxn: Decimal
    costo_total_mxn: Decimal
    margen_mxn: Decimal
    margen_pct: Decimal
    costo_por_km: Decimal
    ingreso_por_km: Decimal
    supuestos: int = 0

    @property
    def en_perdida(self) -> bool:
        return self.margen_mxn < 0

    def as_dict(self) -> dict[str, object]:
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "cliente_id": self.cliente_id,
            "unit_id": self.unit_id,
            "operador_id": self.operador_id,
            "fecha": self.fecha.isoformat(),
            "km": str(self.km),
            "ingreso_mxn": str(self.ingreso_mxn),
            "costo_total_mxn": str(self.costo_total_mxn),
            "margen_mxn": str(self.margen_mxn),
            "margen_pct": str(self.margen_pct),
            "costo_por_km": str(self.costo_por_km),
            "ingreso_por_km": str(self.ingreso_por_km),
            "supuestos": self.supuestos,
        }


def margen_viaje(viaje: Viaje, costeo: ResultadoCosteo) -> MargenViaje:
    """Margen de un viaje contra su costeo.

    El ingreso en cero no es margen -100%: es un viaje sin facturar, y eso es
    un hallazgo distinto. Se bloquea para que no ensucie la distribucion.
    """
    if costeo.trip_id is not None and costeo.trip_id != viaje.trip_id:
        raise ErrorDeValidacion(
            f"el costeo es del viaje {costeo.trip_id} y el viaje es {viaje.trip_id}", campo="trip_id"
        )
    if viaje.ingreso_facturado_mxn <= 0:
        raise ErrorDeValidacion(
            "viaje sin ingreso facturado: revisar facturacion antes de medir margen",
            campo="ingreso_facturado_mxn",
            trip_id=viaje.trip_id,
        )

    ingreso = mxn(viaje.ingreso_facturado_mxn, campo="ingreso_mxn")
    margen = mxn(ingreso - costeo.total_trip_cost, campo="margen_mxn")
    return MargenViaje(
        trip_id=viaje.trip_id,
        route_id=viaje.route_id,
        cliente_id=viaje.cliente_id,
        unit_id=viaje.unit_id,
        operador_id=viaje.operador_id,
        fecha=viaje.fecha_inicio,
        km=costeo.km,
        ingreso_mxn=ingreso,
        costo_total_mxn=costeo.total_trip_cost,
        margen_mxn=margen,
        margen_pct=((margen / ingreso) * 100).quantize(DOS, rounding=ROUND_HALF_UP),
        costo_por_km=costeo.cost_per_km,
        ingreso_por_km=cuota(ingreso / costeo.km, campo="ingreso_por_km"),
        supuestos=len(costeo.assumptions),
    )


# --- agregacion -----------------------------------------------------------

DIMENSIONES: dict[str, Callable[[MargenViaje], str]] = {
    "ruta": lambda m: m.route_id,
    "cliente": lambda m: m.cliente_id,
    "unidad": lambda m: m.unit_id,
    "operador": lambda m: m.operador_id,
}


@dataclass(frozen=True)
class MargenAgregado:
    dimension: str
    clave: str
    viajes: int
    km: Decimal
    ingreso_mxn: Decimal
    costo_mxn: Decimal
    margen_mxn: Decimal
    margen_pct: Decimal
    costo_por_km: Decimal
    margen_pct_mediana: Decimal
    viajes_en_perdida: int

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "clave": self.clave,
            "viajes": self.viajes,
            "km": str(self.km),
            "ingreso_mxn": str(self.ingreso_mxn),
            "costo_mxn": str(self.costo_mxn),
            "margen_mxn": str(self.margen_mxn),
            "margen_pct": str(self.margen_pct),
            "costo_por_km": str(self.costo_por_km),
            "margen_pct_mediana": str(self.margen_pct_mediana),
            "viajes_en_perdida": self.viajes_en_perdida,
        }


def agregar(margenes: Sequence[MargenViaje], dimension: str) -> list[MargenAgregado]:
    """Agrega por ruta, cliente, unidad u operador.

    El margen agregado es ponderado (suma de margenes / suma de ingresos), no
    el promedio de los porcentajes: promediar porcentajes le da el mismo peso
    a un viaje de $3,000 que a uno de $80,000.

    Sale ordenado de peor a mejor margen. Lo que hay que mirar va arriba.
    """
    if dimension not in DIMENSIONES:
        raise ErrorDeValidacion(
            f"dimension desconocida: {dimension!r}; validas: {', '.join(sorted(DIMENSIONES))}", campo="dimension"
        )
    llave = DIMENSIONES[dimension]

    grupos: dict[str, list[MargenViaje]] = {}
    for m in margenes:
        grupos.setdefault(llave(m), []).append(m)

    agregados: list[MargenAgregado] = []
    for clave, items in grupos.items():
        ingreso = sum((m.ingreso_mxn for m in items), Decimal(0))
        costo = sum((m.costo_total_mxn for m in items), Decimal(0))
        km = sum((m.km for m in items), Decimal(0))
        margen = ingreso - costo
        agregados.append(
            MargenAgregado(
                dimension=dimension,
                clave=clave,
                viajes=len(items),
                km=km,
                ingreso_mxn=mxn(ingreso, campo="ingreso_mxn"),
                costo_mxn=mxn(costo, campo="costo_mxn"),
                margen_mxn=mxn(margen, campo="margen_mxn"),
                margen_pct=((margen / ingreso) * 100).quantize(DOS, rounding=ROUND_HALF_UP)
                if ingreso
                else Decimal("0.00"),
                costo_por_km=cuota(costo / km, campo="costo_por_km") if km else Decimal("0.0000"),
                margen_pct_mediana=percentil([m.margen_pct for m in items], Decimal(50)),
                viajes_en_perdida=sum(1 for m in items if m.en_perdida),
            )
        )
    return sorted(agregados, key=lambda a: (a.margen_pct, a.clave))


# --- distribucion (insumo de calibracion de umbrales) ---------------------


def percentil(valores: Sequence[Decimal], p: Decimal) -> Decimal:
    """Percentil por interpolacion lineal sobre la muestra ordenada.

    Deterministico y sin dependencias: el mismo insumo da el mismo umbral
    propuesto, hoy y en la revision de dentro de seis meses.
    """
    if not valores:
        raise ErrorDeValidacion("percentil sobre muestra vacia", campo="valores")
    if not (Decimal(0) <= p <= Decimal(100)):
        raise ErrorDeValidacion(f"percentil fuera de [0, 100]: {p}", campo="p")

    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0].quantize(DOS, rounding=ROUND_HALF_UP)

    posicion = (p / Decimal(100)) * (Decimal(len(ordenados)) - 1)
    inferior = int(posicion)
    superior = min(inferior + 1, len(ordenados) - 1)
    fraccion = posicion - Decimal(inferior)
    valor = ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * fraccion
    return valor.quantize(DOS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Distribucion:
    """Distribucion de margen de un conjunto de viajes.

    Lo que se lleva a la mesa para fijar `margen_objetivo_pct` y
    `margen_minimo_pct` (docs/umbrales.md, paso 2).
    """

    viajes: int
    minimo_pct: Decimal
    p25_pct: Decimal
    mediana_pct: Decimal
    p75_pct: Decimal
    maximo_pct: Decimal
    ponderado_pct: Decimal
    viajes_en_perdida: int
    ingreso_mxn: Decimal
    costo_mxn: Decimal
    margen_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "viajes": self.viajes,
            "minimo_pct": str(self.minimo_pct),
            "p25_pct": str(self.p25_pct),
            "mediana_pct": str(self.mediana_pct),
            "p75_pct": str(self.p75_pct),
            "maximo_pct": str(self.maximo_pct),
            "ponderado_pct": str(self.ponderado_pct),
            "viajes_en_perdida": self.viajes_en_perdida,
            "ingreso_mxn": str(self.ingreso_mxn),
            "costo_mxn": str(self.costo_mxn),
            "margen_mxn": str(self.margen_mxn),
        }


def distribucion(margenes: Sequence[MargenViaje]) -> Distribucion:
    if not margenes:
        raise ErrorDeValidacion("distribucion sobre cero viajes", campo="margenes")
    porcentajes = [m.margen_pct for m in margenes]
    ingreso = sum((m.ingreso_mxn for m in margenes), Decimal(0))
    costo = sum((m.costo_total_mxn for m in margenes), Decimal(0))
    margen = ingreso - costo
    return Distribucion(
        viajes=len(margenes),
        minimo_pct=min(porcentajes),
        p25_pct=percentil(porcentajes, Decimal(25)),
        mediana_pct=percentil(porcentajes, Decimal(50)),
        p75_pct=percentil(porcentajes, Decimal(75)),
        maximo_pct=max(porcentajes),
        ponderado_pct=((margen / ingreso) * 100).quantize(DOS, rounding=ROUND_HALF_UP)
        if ingreso
        else Decimal("0.00"),
        viajes_en_perdida=sum(1 for m in margenes if m.en_perdida),
        ingreso_mxn=mxn(ingreso, campo="ingreso_mxn"),
        costo_mxn=mxn(costo, campo="costo_mxn"),
        margen_mxn=mxn(margen, campo="margen_mxn"),
    )


# --- contraste contra la tabla de precios pre-aprobada --------------------


@dataclass(frozen=True)
class DesviacionTarifa:
    """Un viaje cuyo margen real quedo por debajo del minimo declarado en la tabla.

    Es el hallazgo central que docs/umbrales.md pide producir: la distancia
    entre el margen minimo que la tabla promete y el que la operacion entrega.
    """

    trip_id: str
    route_id: str
    cliente_id: str
    tarifa_id: str
    margen_real_pct: Decimal
    margen_minimo_pct: Decimal
    brecha_pp: Decimal  # puntos porcentuales
    ingreso_mxn: Decimal
    precio_tabla_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "cliente_id": self.cliente_id,
            "tarifa_id": self.tarifa_id,
            "margen_real_pct": str(self.margen_real_pct),
            "margen_minimo_pct": str(self.margen_minimo_pct),
            "brecha_pp": str(self.brecha_pp),
            "ingreso_mxn": str(self.ingreso_mxn),
            "precio_tabla_mxn": str(self.precio_tabla_mxn),
        }


@dataclass
class ContrasteTarifas:
    desviaciones: list[DesviacionTarifa] = field(default_factory=list)
    sin_tarifa: list[str] = field(default_factory=list)
    sin_margen_declarado: list[str] = field(default_factory=list)
    evaluados: int = 0

    def resumen(self) -> dict[str, object]:
        return {
            "evaluados": self.evaluados,
            "desviaciones": len(self.desviaciones),
            "sin_tarifa_vigente": len(self.sin_tarifa),
            "sin_margen_declarado": len(self.sin_margen_declarado),
        }


def contraste_margen_minimo(margenes: Iterable[MargenViaje], catalogo: Catalogo) -> ContrasteTarifas:
    """Compara el margen real de cada viaje contra el minimo de su tarifa vigente."""
    contraste = ContrasteTarifas()
    for m in margenes:
        contraste.evaluados += 1
        tipo_unidad = catalogo.unidades[m.unit_id].tipo if m.unit_id in catalogo.unidades else None
        tarifa = catalogo.tarifa_vigente(
            m.route_id, m.fecha, cliente_id=m.cliente_id, tipo_unidad=tipo_unidad
        )
        if tarifa is None:
            contraste.sin_tarifa.append(m.trip_id)
            continue
        if tarifa.margen_minimo_pct is None:
            contraste.sin_margen_declarado.append(m.trip_id)
            continue
        if m.margen_pct < tarifa.margen_minimo_pct:
            contraste.desviaciones.append(
                DesviacionTarifa(
                    trip_id=m.trip_id,
                    route_id=m.route_id,
                    cliente_id=m.cliente_id,
                    tarifa_id=tarifa.tarifa_id,
                    margen_real_pct=m.margen_pct,
                    margen_minimo_pct=tarifa.margen_minimo_pct.quantize(DOS),
                    brecha_pp=(tarifa.margen_minimo_pct - m.margen_pct).quantize(DOS),
                    ingreso_mxn=m.ingreso_mxn,
                    precio_tabla_mxn=tarifa.precio_mxn,
                )
            )
    contraste.desviaciones.sort(key=lambda d: (-d.brecha_pp, d.trip_id))
    return contraste
