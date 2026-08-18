"""svc-costing - costo por km y por viaje.

El servicio del que cuelga toda la Fase 0. Ocho conceptos, todos con formula
explicita y todos rastreables:

    diesel + casetas + operador + mantenimiento + llantas + seguro +
    depreciacion            = costo variable
    + fijos asignados       = costo total del viaje
    / km                    = costo por km

Tres reglas que no se negocian:

* **Falta un dato, se detiene.** No hay defaults escondidos. Lo unico que se
  deriva es lo que el catalogo permite derivar por aritmetica, y queda escrito
  como supuesto.
* **Un km no positivo bloquea el calculo.** Dividir entre cero produce un
  numero que despues alguien cotiza.
* **Todo Decimal.** Ningun float toca un peso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from services.common.errors import EntradaFaltante, ErrorDeValidacion
from services.common.money import cuota, mxn
from services.common.result import Supuesto, Supuestos
from services.ingest.registros import Viaje
from services.masterdata.catalogo import Catalogo

CONCEPTOS_VARIABLES = (
    "diesel",
    "casetas",
    "operador",
    "mantenimiento",
    "llantas",
    "seguro",
    "depreciacion",
)


@dataclass
class EntradaCosteo:
    """Entradas del contrato registry/services/svc-costing.yaml.

    Todo lo opcional que no venga se resuelve desde svc-masterdata y se
    reporta como supuesto. Lo que no se pueda resolver, detiene el calculo.
    """

    route_id: str
    unit_id: str
    fuel_price: Decimal | None = None
    driver_cost: Decimal | None = None
    tolls: Decimal | None = None
    maintenance_factor: Decimal | None = None
    tire_factor: Decimal | None = None
    insurance_factor: Decimal | None = None
    fixed_cost_allocation: Decimal | None = None
    km: Decimal | None = None
    dias: Decimal | None = None
    operador_id: str | None = None
    trip_id: str | None = None
    fecha: date | None = None


@dataclass
class ResultadoCosteo:
    """Salidas del contrato. `desglose` es lo que hace auditable el total."""

    route_id: str
    unit_id: str
    km: Decimal
    cost_per_km: Decimal
    total_trip_cost: Decimal
    variable_cost: Decimal
    fixed_allocated_cost: Decimal
    desglose: dict[str, Decimal] = field(default_factory=dict)
    assumptions: list[Supuesto] = field(default_factory=list)
    trip_id: str | None = None

    @property
    def variable_cost_per_km(self) -> Decimal:
        return cuota(self.variable_cost / self.km, campo="variable_cost_per_km")

    def as_dict(self) -> dict[str, object]:
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "unit_id": self.unit_id,
            "km": str(self.km),
            "cost_per_km": str(self.cost_per_km),
            "total_trip_cost": str(self.total_trip_cost),
            "variable_cost": str(self.variable_cost),
            "fixed_allocated_cost": str(self.fixed_allocated_cost),
            "desglose": {concepto: str(importe) for concepto, importe in self.desglose.items()},
            "assumptions": [s.as_dict() for s in self.assumptions],
        }


def costear(entrada: EntradaCosteo, catalogo: Catalogo) -> ResultadoCosteo:
    """Costea un viaje. Deterministico: mismas entradas, mismo resultado, siempre."""
    ruta = catalogo.ruta(entrada.route_id)
    unidad = catalogo.unidad(entrada.unit_id)
    supuestos = Supuestos()

    km = entrada.km
    if km is None:
        km = supuestos.registrar("km", ruta.km, "masterdata", f"km de la ruta {ruta.route_id}")
    if km <= 0:
        raise ErrorDeValidacion(
            f"distancia no positiva ({km}): el costo por km seria indefinido", campo="km", route_id=ruta.route_id
        )

    dias = entrada.dias
    if dias is None:
        dias = supuestos.registrar(
            "dias", ruta.dias_estimados, "masterdata", f"dias estimados de la ruta {ruta.route_id}"
        )

    desglose: dict[str, Decimal] = {}
    desglose["diesel"] = _diesel(entrada, unidad, km, catalogo, supuestos)
    desglose["casetas"] = _casetas(entrada, ruta, supuestos)
    desglose["operador"] = _operador(entrada, km, dias, catalogo, supuestos)
    desglose["mantenimiento"] = _por_km(
        entrada.maintenance_factor,
        unidad.mantenimiento_mxn_km,
        km,
        campo="maintenance_factor",
        detalle=f"mantenimiento por km de la unidad {unidad.unit_id}",
        supuestos=supuestos,
    )
    desglose["llantas"] = _llantas(entrada, unidad, km, supuestos)
    desglose["seguro"] = _seguro(entrada, unidad, km, supuestos)
    desglose["depreciacion"] = _depreciacion(unidad, km, supuestos)

    variable = sum((desglose[c] for c in CONCEPTOS_VARIABLES), Decimal(0))
    fijos = _fijos(entrada, km, catalogo, supuestos)
    total = mxn(variable + fijos, campo="total_trip_cost")

    return ResultadoCosteo(
        route_id=ruta.route_id,
        unit_id=unidad.unit_id,
        km=km,
        cost_per_km=cuota(total / km, campo="cost_per_km"),
        total_trip_cost=total,
        variable_cost=mxn(variable, campo="variable_cost"),
        fixed_allocated_cost=fijos,
        desglose=desglose,
        assumptions=list(supuestos),
        trip_id=entrada.trip_id,
    )


def costear_viaje(
    viaje: Viaje,
    catalogo: Catalogo,
    *,
    fuel_price: Decimal | None = None,
    km_reales: Decimal | None = None,
) -> ResultadoCosteo:
    """Costea a partir de un registro de svc-ingest.

    `km_reales` permite usar los km del GPS en vez de los de la ruta: la
    diferencia entre ambos es, literalmente, costo que el catalogo no ve.
    """
    return costear(
        EntradaCosteo(
            route_id=viaje.route_id,
            unit_id=viaje.unit_id,
            operador_id=viaje.operador_id,
            trip_id=viaje.trip_id,
            fuel_price=fuel_price,
            km=km_reales if km_reales is not None else viaje.km_recorridos,
            dias=Decimal(viaje.dias),
            fecha=viaje.fecha_inicio,
        ),
        catalogo,
    )


# --- conceptos ------------------------------------------------------------


def _diesel(
    entrada: EntradaCosteo, unidad, km: Decimal, catalogo: Catalogo, supuestos: Supuestos
) -> Decimal:
    precio = entrada.fuel_price
    if precio is None:
        referencia = catalogo.parametros.precio_diesel_mxn_litro if catalogo.parametros else None
        if referencia is None:
            raise EntradaFaltante(
                "falta el precio del diesel y el catalogo no trae precio de referencia",
                campo="fuel_price",
                unit_id=unidad.unit_id,
            )
        precio = supuestos.registrar(
            "fuel_price", referencia, "parametro", "precio de diesel de referencia del catalogo, no del ticket del viaje"
        )
    if precio <= 0:
        raise ErrorDeValidacion(f"precio de diesel no positivo ({precio})", campo="fuel_price")
    litros = km / unidad.rendimiento_km_l
    return mxn(litros * precio, campo="diesel")


def _casetas(entrada: EntradaCosteo, ruta, supuestos: Supuestos) -> Decimal:
    if entrada.tolls is not None:
        if entrada.tolls < 0:
            raise ErrorDeValidacion("casetas negativas", campo="tolls")
        return mxn(entrada.tolls, campo="casetas")
    return mxn(
        supuestos.registrar("tolls", ruta.casetas_mxn, "masterdata", f"casetas de la ruta {ruta.route_id}"),
        campo="casetas",
    )


def _operador(
    entrada: EntradaCosteo, km: Decimal, dias: Decimal, catalogo: Catalogo, supuestos: Supuestos
) -> Decimal:
    if entrada.driver_cost is not None:
        if entrada.driver_cost < 0:
            raise ErrorDeValidacion("costo de operador negativo", campo="driver_cost")
        return mxn(entrada.driver_cost, campo="operador")

    if not entrada.operador_id:
        raise EntradaFaltante(
            "sin driver_cost y sin operador_id: no hay forma de costear al operador", campo="driver_cost"
        )
    operador = catalogo.operador(entrada.operador_id)

    costo = Decimal(0)
    if operador.esquema_pago in ("km", "mixto"):
        costo += operador.pago_mxn_km * km
    if operador.esquema_pago in ("fijo", "mixto"):
        if operador.viajes_mensuales_esperados <= 0:
            raise EntradaFaltante(
                "el operador cobra sueldo fijo pero no declara viajes mensuales esperados: "
                "el prorrateo al viaje seria arbitrario",
                campo="viajes_mensuales_esperados",
                operador_id=operador.operador_id,
            )
        costo += operador.sueldo_mensual_mxn / operador.viajes_mensuales_esperados
    costo += operador.viaticos_mxn_dia * dias

    importe = mxn(costo, campo="operador")
    supuestos.registrar(
        "driver_cost", importe, "derivado", f"esquema {operador.esquema_pago} del operador {operador.operador_id}"
    )
    return importe


def _por_km(
    valor_entrada: Decimal | None,
    valor_catalogo: Decimal,
    km: Decimal,
    *,
    campo: str,
    detalle: str,
    supuestos: Supuestos,
) -> Decimal:
    if valor_entrada is not None:
        if valor_entrada < 0:
            raise ErrorDeValidacion(f"{campo} negativo", campo=campo)
        return mxn(valor_entrada * km, campo=campo)
    supuestos.registrar(campo, valor_catalogo, "masterdata", detalle)
    return mxn(valor_catalogo * km, campo=campo)


def _llantas(entrada: EntradaCosteo, unidad, km: Decimal, supuestos: Supuestos) -> Decimal:
    if entrada.tire_factor is not None:
        if entrada.tire_factor < 0:
            raise ErrorDeValidacion("tire_factor negativo", campo="tire_factor")
        return mxn(entrada.tire_factor * km, campo="llantas")
    if unidad.costo_juego_llantas_mxn <= 0:
        supuestos.registrar("tire_factor", Decimal(0), "masterdata", f"unidad {unidad.unit_id} sin costo de llantas")
        return Decimal("0.00")
    factor = cuota(unidad.costo_juego_llantas_mxn / unidad.vida_llantas_km, campo="tire_factor")
    supuestos.registrar(
        "tire_factor", factor, "derivado", f"juego de llantas / vida en km de la unidad {unidad.unit_id}"
    )
    return mxn(factor * km, campo="llantas")


def _seguro(entrada: EntradaCosteo, unidad, km: Decimal, supuestos: Supuestos) -> Decimal:
    if entrada.insurance_factor is not None:
        if entrada.insurance_factor < 0:
            raise ErrorDeValidacion("insurance_factor negativo", campo="insurance_factor")
        return mxn(entrada.insurance_factor * km, campo="seguro")
    if unidad.poliza_anual_mxn <= 0:
        supuestos.registrar("insurance_factor", Decimal(0), "masterdata", f"unidad {unidad.unit_id} sin poliza")
        return Decimal("0.00")
    factor = cuota(unidad.poliza_anual_mxn / unidad.km_anuales_esperados, campo="insurance_factor")
    supuestos.registrar(
        "insurance_factor", factor, "derivado", f"poliza anual / km anuales esperados de la unidad {unidad.unit_id}"
    )
    return mxn(factor * km, campo="seguro")


def _depreciacion(unidad, km: Decimal, supuestos: Supuestos) -> Decimal:
    """Lineal por kilometro. Sin valor de adquisicion o sin vida util, es cero y se dice."""
    if unidad.costo_adquisicion_mxn <= 0 or unidad.vida_util_km <= 0:
        supuestos.registrar(
            "depreciacion_mxn_km",
            Decimal(0),
            "masterdata",
            f"unidad {unidad.unit_id} sin costo de adquisicion o sin vida util: el costo por km queda subestimado",
        )
        return Decimal("0.00")
    factor = cuota(
        (unidad.costo_adquisicion_mxn - unidad.valor_residual_mxn) / unidad.vida_util_km,
        campo="depreciacion_mxn_km",
    )
    supuestos.registrar(
        "depreciacion_mxn_km", factor, "derivado", f"(adquisicion - residual) / vida util de la unidad {unidad.unit_id}"
    )
    return mxn(factor * km, campo="depreciacion")


def _fijos(entrada: EntradaCosteo, km: Decimal, catalogo: Catalogo, supuestos: Supuestos) -> Decimal:
    if entrada.fixed_cost_allocation is not None:
        if entrada.fixed_cost_allocation < 0:
            raise ErrorDeValidacion("fixed_cost_allocation negativo", campo="fixed_cost_allocation")
        return mxn(entrada.fixed_cost_allocation, campo="fixed_allocated_cost")

    parametros = catalogo.parametros
    if parametros is None or parametros.costos_fijos_mensuales_mxn <= 0:
        supuestos.registrar(
            "fixed_cost_allocation",
            Decimal(0),
            "parametro",
            "el catalogo no declara costos fijos mensuales: el costo por km es solo variable",
        )
        return Decimal("0.00")

    if parametros.base_asignacion_fijos == "km":
        if parametros.km_mensuales_flota <= 0:
            raise EntradaFaltante(
                "asignacion de fijos por km sin km mensuales de flota", campo="km_mensuales_flota"
            )
        factor = cuota(parametros.costos_fijos_mensuales_mxn / parametros.km_mensuales_flota, campo="fijos_mxn_km")
        importe = mxn(factor * km, campo="fixed_allocated_cost")
        detalle = "costos fijos mensuales / km mensuales de flota"
    else:
        if parametros.viajes_mensuales_flota <= 0:
            raise EntradaFaltante(
                "asignacion de fijos por viaje sin viajes mensuales de flota", campo="viajes_mensuales_flota"
            )
        importe = mxn(
            parametros.costos_fijos_mensuales_mxn / parametros.viajes_mensuales_flota, campo="fixed_allocated_cost"
        )
        detalle = "costos fijos mensuales / viajes mensuales de flota"

    supuestos.registrar("fixed_cost_allocation", importe, "parametro", detalle)
    return importe
