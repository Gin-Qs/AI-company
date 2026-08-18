"""Corrida completa de la Fase 0: catalogo -> ingesta -> costeo -> margen.

Cuatro servicios encadenados, cero agentes, cero ACT-*. Lo que produce esta
corrida es exactamente el entregable de la fase segun el roadmap (seccion 15):
costo por km y margen real por viaje, ruta, cliente, unidad y operador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from services.common.errors import ErrorDeServicio
from services.costing.motor import ResultadoCosteo, costear_viaje
from services.ingest.normalizador import (
    ResultadoIngesta,
    normalizar_banco,
    normalizar_diesel,
    normalizar_gps,
    normalizar_viajes,
    precio_diesel_promedio,
)
from services.ingest.registros import CargaDiesel, Viaje
from services.masterdata.catalogo import Catalogo
from services.masterdata.loader import cargar_catalogo, leer_csv
from services.profitability.margen import (
    ContrasteTarifas,
    Distribucion,
    MargenAgregado,
    MargenViaje,
    agregar,
    contraste_margen_minimo,
    distribucion,
    margen_viaje,
)

SUBDIR_CATALOGO = "catalogo"
SUBDIR_OPERACION = "operacion"
ARCHIVOS_OPERACION = {
    "viajes": "viajes.csv",
    "diesel": "diesel.csv",
    "gps": "gps.csv",
    "banco": "banco.csv",
}


@dataclass(frozen=True)
class ViajeNoCosteado:
    trip_id: str
    codigo: str
    motivo: str

    def as_dict(self) -> dict[str, str]:
        return {"trip_id": self.trip_id, "codigo": self.codigo, "motivo": self.motivo}


@dataclass
class ReporteFase0:
    catalogo: Catalogo
    ingestas: dict[str, ResultadoIngesta] = field(default_factory=dict)
    costeos: list[ResultadoCosteo] = field(default_factory=list)
    margenes: list[MargenViaje] = field(default_factory=list)
    agregados: dict[str, list[MargenAgregado]] = field(default_factory=dict)
    distribucion: Distribucion | None = None
    contraste: ContrasteTarifas | None = None
    no_costeados: list[ViajeNoCosteado] = field(default_factory=list)
    precios_diesel: dict[str, Decimal] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "catalogo": self.catalogo.resumen(),
            "ingesta": {nombre: resultado.resumen() for nombre, resultado in self.ingestas.items()},
            "precios_diesel_mxn_litro": {periodo: str(p) for periodo, p in sorted(self.precios_diesel.items())},
            "viajes_costeados": len(self.costeos),
            "no_costeados": [v.as_dict() for v in self.no_costeados],
            "distribucion_margen": self.distribucion.as_dict() if self.distribucion else None,
            "margen_por": {
                dimension: [a.as_dict() for a in agregados] for dimension, agregados in self.agregados.items()
            },
            "contraste_tarifas": self.contraste.resumen() if self.contraste else None,
            "desviaciones_tarifa": [d.as_dict() for d in self.contraste.desviaciones] if self.contraste else [],
            "viajes": [m.as_dict() for m in self.margenes],
        }


def _filas(ruta: Path) -> list[dict[str, str]]:
    return list(leer_csv(ruta)) if ruta.is_file() else []


def _periodo(anio: int, mes: int) -> str:
    return f"{anio:04d}-{mes:02d}"


def precios_diesel_por_periodo(cargas: list[CargaDiesel]) -> dict[str, Decimal]:
    """Precio ponderado por litros, por mes.

    El diesel se mueve mes a mes; usar el promedio del trimestre para costear
    un viaje de enero mete un sesgo que despues nadie encuentra.
    """
    periodos: dict[str, list[CargaDiesel]] = {}
    for carga in cargas:
        periodos.setdefault(_periodo(carga.fecha.year, carga.fecha.month), []).append(carga)
    precios = {periodo: precio_diesel_promedio(items) for periodo, items in periodos.items()}
    return {periodo: precio for periodo, precio in precios.items() if precio is not None}


def _precio_para(viaje: Viaje, precios: dict[str, Decimal], global_: Decimal | None) -> Decimal | None:
    return precios.get(_periodo(viaje.fecha_inicio.year, viaje.fecha_inicio.month)) or global_


def ejecutar_fase0(directorio: str | Path) -> ReporteFase0:
    """Corre la fase completa sobre un directorio de datos.

    Estructura esperada:

        <directorio>/catalogo/{clientes,unidades,operadores,rutas,tarifas}.csv
        <directorio>/catalogo/parametros.yaml
        <directorio>/operacion/{viajes,diesel,gps,banco}.csv   (banco y gps opcionales)
    """
    base = Path(directorio)
    catalogo = cargar_catalogo(base / SUBDIR_CATALOGO)
    operacion = base / SUBDIR_OPERACION

    ingesta_viajes = normalizar_viajes(
        _filas(operacion / ARCHIVOS_OPERACION["viajes"]), catalogo=catalogo, solo_cerrados=True
    )
    ingesta_diesel = normalizar_diesel(_filas(operacion / ARCHIVOS_OPERACION["diesel"]), catalogo=catalogo)
    ingesta_gps = normalizar_gps(_filas(operacion / ARCHIVOS_OPERACION["gps"]))
    ingesta_banco = normalizar_banco(_filas(operacion / ARCHIVOS_OPERACION["banco"]))

    reporte = ReporteFase0(
        catalogo=catalogo,
        ingestas={
            "viajes": ingesta_viajes,
            "diesel": ingesta_diesel,
            "gps": ingesta_gps,
            "banco": ingesta_banco,
        },
    )

    cargas = list(ingesta_diesel.registros)
    reporte.precios_diesel = precios_diesel_por_periodo(cargas)
    precio_global = precio_diesel_promedio(cargas)

    km_gps = {
        (recorrido.unit_id, recorrido.trip_id): recorrido.km_recorridos
        for recorrido in ingesta_gps.registros
        if recorrido.trip_id
    }

    for viaje in ingesta_viajes.registros:
        try:
            costeo = costear_viaje(
                viaje,
                catalogo,
                fuel_price=_precio_para(viaje, reporte.precios_diesel, precio_global),
                km_reales=viaje.km_recorridos or km_gps.get((viaje.unit_id, viaje.trip_id)),
            )
            margen = margen_viaje(viaje, costeo)
        except ErrorDeServicio as exc:
            reporte.no_costeados.append(ViajeNoCosteado(viaje.trip_id, exc.codigo, exc.mensaje))
            continue
        reporte.costeos.append(costeo)
        reporte.margenes.append(margen)

    if reporte.margenes:
        reporte.distribucion = distribucion(reporte.margenes)
        reporte.agregados = {
            dimension: agregar(reporte.margenes, dimension)
            for dimension in ("ruta", "cliente", "unidad", "operador")
        }
        reporte.contraste = contraste_margen_minimo(reporte.margenes, catalogo)

    return reporte
