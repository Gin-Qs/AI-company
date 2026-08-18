"""Entidades del catalogo unico (svc-masterdata).

Un solo lugar donde vive cada cliente, unidad, operador, ruta y tarifa. El
hueco que antes llenaba cada agente con su propia copia del dato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from services.common.errors import ErrorDeValidacion
from services.common.money import cantidad, cuota, mxn, no_negativo, positivo

FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y")


def fecha(valor: object, *, campo: str = "fecha") -> date:
    """Acepta los formatos que de hecho llegan del ERP y de los tickets de papel."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        raise ErrorDeValidacion("fecha vacia", campo=campo)
    texto = texto.split("T")[0].split(" ")[0]
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErrorDeValidacion(f"fecha no reconocida: {valor!r}", campo=campo)


def booleano(valor: object, *, default: bool = True) -> bool:
    texto = str(valor if valor is not None else "").strip().lower()
    if texto == "":
        return default
    return texto in {"1", "si", "true", "verdadero", "x", "activo", "y", "yes"}


def texto_requerido(valor: object, *, campo: str) -> str:
    limpio = str(valor or "").strip()
    if not limpio:
        raise ErrorDeValidacion("valor obligatorio vacio", campo=campo)
    return limpio


@dataclass(frozen=True)
class Cliente:
    cliente_id: str
    nombre: str
    rfc: str
    dias_credito: int
    activo: bool = True

    @classmethod
    def desde_fila(cls, fila: dict[str, str]) -> "Cliente":
        return cls(
            cliente_id=texto_requerido(fila.get("cliente_id"), campo="cliente_id"),
            nombre=texto_requerido(fila.get("nombre"), campo="nombre"),
            rfc=str(fila.get("rfc") or "").strip().upper(),
            dias_credito=int(cantidad(fila.get("dias_credito") or 0, campo="dias_credito")),
            activo=booleano(fila.get("activo")),
        )


@dataclass(frozen=True)
class Unidad:
    """Tractocamion o unidad de reparto. Trae consigo su propia estructura de costo."""

    unit_id: str
    placa: str
    tipo: str
    rendimiento_km_l: Decimal
    costo_adquisicion_mxn: Decimal
    valor_residual_mxn: Decimal
    vida_util_km: Decimal
    mantenimiento_mxn_km: Decimal
    costo_juego_llantas_mxn: Decimal
    vida_llantas_km: Decimal
    poliza_anual_mxn: Decimal
    km_anuales_esperados: Decimal
    modelo_anio: int | None = None
    activo: bool = True

    @classmethod
    def desde_fila(cls, fila: dict[str, str]) -> "Unidad":
        uid = texto_requerido(fila.get("unit_id"), campo="unit_id")
        anio = str(fila.get("modelo_anio") or "").strip()
        return cls(
            unit_id=uid,
            placa=str(fila.get("placa") or "").strip().upper(),
            tipo=texto_requerido(fila.get("tipo"), campo=f"unidades[{uid}].tipo"),
            rendimiento_km_l=positivo(
                cuota(fila.get("rendimiento_km_l"), campo=f"unidades[{uid}].rendimiento_km_l"),
                campo=f"unidades[{uid}].rendimiento_km_l",
            ),
            costo_adquisicion_mxn=no_negativo(
                mxn(fila.get("costo_adquisicion_mxn") or 0), campo=f"unidades[{uid}].costo_adquisicion_mxn"
            ),
            valor_residual_mxn=no_negativo(
                mxn(fila.get("valor_residual_mxn") or 0), campo=f"unidades[{uid}].valor_residual_mxn"
            ),
            vida_util_km=no_negativo(cantidad(fila.get("vida_util_km") or 0), campo=f"unidades[{uid}].vida_util_km"),
            mantenimiento_mxn_km=no_negativo(
                cuota(fila.get("mantenimiento_mxn_km") or 0), campo=f"unidades[{uid}].mantenimiento_mxn_km"
            ),
            costo_juego_llantas_mxn=no_negativo(
                mxn(fila.get("costo_juego_llantas_mxn") or 0), campo=f"unidades[{uid}].costo_juego_llantas_mxn"
            ),
            vida_llantas_km=no_negativo(
                cantidad(fila.get("vida_llantas_km") or 0), campo=f"unidades[{uid}].vida_llantas_km"
            ),
            poliza_anual_mxn=no_negativo(
                mxn(fila.get("poliza_anual_mxn") or 0), campo=f"unidades[{uid}].poliza_anual_mxn"
            ),
            km_anuales_esperados=no_negativo(
                cantidad(fila.get("km_anuales_esperados") or 0), campo=f"unidades[{uid}].km_anuales_esperados"
            ),
            modelo_anio=int(anio) if anio else None,
            activo=booleano(fila.get("activo")),
        )


@dataclass(frozen=True)
class Operador:
    operador_id: str
    nombre: str
    esquema_pago: str  # km | fijo | mixto
    pago_mxn_km: Decimal
    sueldo_mensual_mxn: Decimal
    viaticos_mxn_dia: Decimal
    viajes_mensuales_esperados: Decimal
    activo: bool = True

    ESQUEMAS = ("km", "fijo", "mixto")

    @classmethod
    def desde_fila(cls, fila: dict[str, str]) -> "Operador":
        oid = texto_requerido(fila.get("operador_id"), campo="operador_id")
        esquema = str(fila.get("esquema_pago") or "km").strip().lower()
        if esquema not in cls.ESQUEMAS:
            raise ErrorDeValidacion(
                f"esquema de pago desconocido: {esquema!r}", campo=f"operadores[{oid}].esquema_pago"
            )
        return cls(
            operador_id=oid,
            nombre=texto_requerido(fila.get("nombre"), campo=f"operadores[{oid}].nombre"),
            esquema_pago=esquema,
            pago_mxn_km=no_negativo(cuota(fila.get("pago_mxn_km") or 0), campo=f"operadores[{oid}].pago_mxn_km"),
            sueldo_mensual_mxn=no_negativo(
                mxn(fila.get("sueldo_mensual_mxn") or 0), campo=f"operadores[{oid}].sueldo_mensual_mxn"
            ),
            viaticos_mxn_dia=no_negativo(
                mxn(fila.get("viaticos_mxn_dia") or 0), campo=f"operadores[{oid}].viaticos_mxn_dia"
            ),
            viajes_mensuales_esperados=no_negativo(
                cantidad(fila.get("viajes_mensuales_esperados") or 0),
                campo=f"operadores[{oid}].viajes_mensuales_esperados",
            ),
            activo=booleano(fila.get("activo")),
        )


@dataclass(frozen=True)
class Ruta:
    route_id: str
    origen: str
    destino: str
    km: Decimal
    casetas_mxn: Decimal
    dias_estimados: Decimal
    activo: bool = True

    @classmethod
    def desde_fila(cls, fila: dict[str, str]) -> "Ruta":
        rid = texto_requerido(fila.get("route_id"), campo="route_id")
        return cls(
            route_id=rid,
            origen=texto_requerido(fila.get("origen"), campo=f"rutas[{rid}].origen"),
            destino=texto_requerido(fila.get("destino"), campo=f"rutas[{rid}].destino"),
            km=positivo(cantidad(fila.get("km"), campo=f"rutas[{rid}].km"), campo=f"rutas[{rid}].km"),
            casetas_mxn=no_negativo(mxn(fila.get("casetas_mxn") or 0), campo=f"rutas[{rid}].casetas_mxn"),
            dias_estimados=no_negativo(cantidad(fila.get("dias_estimados") or 1), campo=f"rutas[{rid}].dias_estimados"),
            activo=booleano(fila.get("activo")),
        )


@dataclass(frozen=True)
class Tarifa:
    """Renglon de la tabla de precios pre-aprobada.

    No la inventa el sistema: es la tabla que Gabriel fija por ruta y actualiza
    cada mes (docs/umbrales.md). svc-masterdata la versiona y la deja
    consultable; svc-pricing la consumira en la Fase 1 como dato maestro.
    """

    tarifa_id: str
    route_id: str
    precio_mxn: Decimal
    margen_minimo_pct: Decimal | None
    vigencia_desde: date
    vigencia_hasta: date | None
    version: str
    cliente_id: str | None = None
    tipo_unidad: str | None = None
    autorizado_por: str = ""

    @classmethod
    def desde_fila(cls, fila: dict[str, str]) -> "Tarifa":
        tid = texto_requerido(fila.get("tarifa_id"), campo="tarifa_id")
        hasta = str(fila.get("vigencia_hasta") or "").strip()
        margen = str(fila.get("margen_minimo_pct") or "").strip()
        cliente = str(fila.get("cliente_id") or "").strip()
        tipo = str(fila.get("tipo_unidad") or "").strip()
        return cls(
            tarifa_id=tid,
            route_id=texto_requerido(fila.get("route_id"), campo=f"tarifas[{tid}].route_id"),
            precio_mxn=positivo(
                mxn(fila.get("precio_mxn"), campo=f"tarifas[{tid}].precio_mxn"), campo=f"tarifas[{tid}].precio_mxn"
            ),
            margen_minimo_pct=cuota(margen, campo=f"tarifas[{tid}].margen_minimo_pct") if margen else None,
            vigencia_desde=fecha(fila.get("vigencia_desde"), campo=f"tarifas[{tid}].vigencia_desde"),
            vigencia_hasta=fecha(hasta, campo=f"tarifas[{tid}].vigencia_hasta") if hasta else None,
            version=str(fila.get("version") or "v1").strip(),
            cliente_id=cliente or None,
            tipo_unidad=tipo or None,
            autorizado_por=str(fila.get("autorizado_por") or "").strip(),
        )

    def vigente_en(self, dia: date) -> bool:
        if dia < self.vigencia_desde:
            return False
        return self.vigencia_hasta is None or dia <= self.vigencia_hasta

    @property
    def especificidad(self) -> int:
        """Cuanto mas especifica, mas manda: cliente+tipo (3) > cliente (2) > tipo (1) > general (0)."""
        return (2 if self.cliente_id else 0) + (1 if self.tipo_unidad else 0)


@dataclass(frozen=True)
class Parametros:
    """Parametros de empresa. Lo que no pertenece a una unidad ni a una ruta."""

    costos_fijos_mensuales_mxn: Decimal
    base_asignacion_fijos: str  # km | viaje
    km_mensuales_flota: Decimal
    viajes_mensuales_flota: Decimal
    precio_diesel_mxn_litro: Decimal | None
    moneda: str = "MXN"
    version: str = "v1"

    BASES = ("km", "viaje")

    @classmethod
    def desde_dict(cls, datos: dict[str, object]) -> "Parametros":
        base = str(datos.get("base_asignacion_fijos") or "km").strip().lower()
        if base not in cls.BASES:
            raise ErrorDeValidacion(f"base de asignacion desconocida: {base!r}", campo="base_asignacion_fijos")
        diesel = datos.get("precio_diesel_mxn_litro")
        return cls(
            costos_fijos_mensuales_mxn=no_negativo(
                mxn(datos.get("costos_fijos_mensuales_mxn") or 0), campo="costos_fijos_mensuales_mxn"
            ),
            base_asignacion_fijos=base,
            km_mensuales_flota=no_negativo(cantidad(datos.get("km_mensuales_flota") or 0), campo="km_mensuales_flota"),
            viajes_mensuales_flota=no_negativo(
                cantidad(datos.get("viajes_mensuales_flota") or 0), campo="viajes_mensuales_flota"
            ),
            precio_diesel_mxn_litro=cuota(diesel, campo="precio_diesel_mxn_litro") if diesel else None,
            moneda=str(datos.get("moneda") or "MXN"),
            version=str(datos.get("version") or "v1"),
        )
