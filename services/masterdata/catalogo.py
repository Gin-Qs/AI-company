"""Catalogo unico y sus consultas (svc-masterdata).

El catalogo es de solo lectura una vez construido. Quien quiera cambiar un
dato maestro cambia el archivo de origen y vuelve a cargar: asi el numero que
uso un calculo siempre se puede reconstruir a partir de una version del
catalogo, que es lo que exige la trazabilidad de la seccion 8.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from services.common.errors import ErrorDeIntegridad
from services.masterdata.models import (
    Cliente,
    Operador,
    Parametros,
    Ruta,
    Tarifa,
    Unidad,
)


@dataclass(frozen=True)
class ProblemaDeIntegridad:
    entidad: str
    identificador: str
    problema: str

    def __str__(self) -> str:  # pragma: no cover - formato
        return f"{self.entidad}[{self.identificador}]: {self.problema}"


@dataclass
class Catalogo:
    """Las cinco entidades maestras mas los parametros de empresa."""

    clientes: dict[str, Cliente] = field(default_factory=dict)
    unidades: dict[str, Unidad] = field(default_factory=dict)
    operadores: dict[str, Operador] = field(default_factory=dict)
    rutas: dict[str, Ruta] = field(default_factory=dict)
    tarifas: list[Tarifa] = field(default_factory=list)
    parametros: Parametros | None = None
    version: str = "v1"

    # --- consultas -------------------------------------------------------

    def cliente(self, cliente_id: str) -> Cliente:
        return self._buscar(self.clientes, cliente_id, "cliente")

    def unidad(self, unit_id: str) -> Unidad:
        return self._buscar(self.unidades, unit_id, "unidad")

    def operador(self, operador_id: str) -> Operador:
        return self._buscar(self.operadores, operador_id, "operador")

    def ruta(self, route_id: str) -> Ruta:
        return self._buscar(self.rutas, route_id, "ruta")

    @staticmethod
    def _buscar(indice: dict[str, object], clave: str, entidad: str):
        try:
            return indice[clave]
        except KeyError:
            raise ErrorDeIntegridad(
                f"{entidad} inexistente en el catalogo: {clave!r}", campo=entidad, identificador=clave
            ) from None

    def tarifa_vigente(
        self,
        route_id: str,
        dia: date,
        *,
        cliente_id: str | None = None,
        tipo_unidad: str | None = None,
    ) -> Tarifa | None:
        """Tarifa aplicable a una ruta en una fecha.

        Gana la mas especifica; a igual especificidad, la de vigencia mas
        reciente; y si dos empatan tambien ahi, la de version mayor. Nunca
        elige al azar: dos tarifas identicas en todo son un problema de datos
        que reporta `validar()`, no algo que resuelva el desempate.
        """
        candidatas = [
            t
            for t in self.tarifas
            if t.route_id == route_id
            and t.vigente_en(dia)
            and (t.cliente_id is None or t.cliente_id == cliente_id)
            and (t.tipo_unidad is None or t.tipo_unidad == tipo_unidad)
        ]
        if not candidatas:
            return None
        return max(candidatas, key=lambda t: (t.especificidad, t.vigencia_desde, t.version))

    # --- integridad ------------------------------------------------------

    def validar(self) -> list[ProblemaDeIntegridad]:
        """Devuelve todos los problemas, no solo el primero.

        Un cargador que revienta en el primer error obliga a diez rondas de
        correccion. Este devuelve la lista completa para arreglarla de una vez.
        """
        problemas: list[ProblemaDeIntegridad] = []

        if self.parametros is None:
            problemas.append(ProblemaDeIntegridad("parametros", "-", "faltan los parametros de empresa"))
        else:
            p = self.parametros
            if p.costos_fijos_mensuales_mxn > 0:
                if p.base_asignacion_fijos == "km" and p.km_mensuales_flota <= 0:
                    problemas.append(
                        ProblemaDeIntegridad(
                            "parametros", "km_mensuales_flota", "base de asignacion por km sin km mensuales de flota"
                        )
                    )
                if p.base_asignacion_fijos == "viaje" and p.viajes_mensuales_flota <= 0:
                    problemas.append(
                        ProblemaDeIntegridad(
                            "parametros",
                            "viajes_mensuales_flota",
                            "base de asignacion por viaje sin viajes mensuales de flota",
                        )
                    )

        for unidad in self.unidades.values():
            if unidad.costo_adquisicion_mxn > 0 and unidad.vida_util_km <= 0:
                problemas.append(
                    ProblemaDeIntegridad("unidad", unidad.unit_id, "tiene costo de adquisicion pero no vida util en km")
                )
            if unidad.valor_residual_mxn > unidad.costo_adquisicion_mxn:
                problemas.append(
                    ProblemaDeIntegridad("unidad", unidad.unit_id, "valor residual mayor que costo de adquisicion")
                )
            if unidad.costo_juego_llantas_mxn > 0 and unidad.vida_llantas_km <= 0:
                problemas.append(
                    ProblemaDeIntegridad("unidad", unidad.unit_id, "tiene costo de llantas pero no vida en km")
                )
            if unidad.poliza_anual_mxn > 0 and unidad.km_anuales_esperados <= 0:
                problemas.append(
                    ProblemaDeIntegridad("unidad", unidad.unit_id, "tiene poliza anual pero no km anuales esperados")
                )

        for operador in self.operadores.values():
            if operador.esquema_pago in ("fijo", "mixto"):
                if operador.sueldo_mensual_mxn <= 0:
                    problemas.append(
                        ProblemaDeIntegridad("operador", operador.operador_id, "esquema con sueldo fijo sin sueldo")
                    )
                elif operador.viajes_mensuales_esperados <= 0:
                    problemas.append(
                        ProblemaDeIntegridad(
                            "operador",
                            operador.operador_id,
                            "sueldo fijo sin viajes mensuales esperados: no hay como prorratearlo al viaje",
                        )
                    )
            if operador.esquema_pago in ("km", "mixto") and operador.pago_mxn_km <= 0:
                problemas.append(
                    ProblemaDeIntegridad("operador", operador.operador_id, "esquema por km sin pago por km")
                )

        vistos: set[tuple] = set()
        for tarifa in self.tarifas:
            if tarifa.route_id not in self.rutas:
                problemas.append(
                    ProblemaDeIntegridad("tarifa", tarifa.tarifa_id, f"ruta inexistente: {tarifa.route_id}")
                )
            if tarifa.cliente_id and tarifa.cliente_id not in self.clientes:
                problemas.append(
                    ProblemaDeIntegridad("tarifa", tarifa.tarifa_id, f"cliente inexistente: {tarifa.cliente_id}")
                )
            if tarifa.vigencia_hasta and tarifa.vigencia_hasta < tarifa.vigencia_desde:
                problemas.append(ProblemaDeIntegridad("tarifa", tarifa.tarifa_id, "vigencia invertida"))
            if tarifa.margen_minimo_pct is not None and not (Decimal(0) <= tarifa.margen_minimo_pct < Decimal(100)):
                problemas.append(
                    ProblemaDeIntegridad("tarifa", tarifa.tarifa_id, "margen minimo fuera del rango [0, 100)")
                )
            clave = (
                tarifa.route_id,
                tarifa.cliente_id,
                tarifa.tipo_unidad,
                tarifa.vigencia_desde,
                tarifa.version,
            )
            if clave in vistos:
                problemas.append(
                    ProblemaDeIntegridad(
                        "tarifa", tarifa.tarifa_id, "duplicada: misma ruta, cliente, tipo, vigencia y version"
                    )
                )
            vistos.add(clave)

        return problemas

    def exigir_integridad(self) -> None:
        problemas = self.validar()
        if problemas:
            detalle = "; ".join(str(p) for p in problemas)
            raise ErrorDeIntegridad(
                f"el catalogo tiene {len(problemas)} problema(s) de integridad: {detalle}",
                campo="catalogo",
                problemas=[p.__dict__ for p in problemas],
            )

    # --- resumen ---------------------------------------------------------

    def resumen(self) -> dict[str, int]:
        return {
            "clientes": len(self.clientes),
            "unidades": len(self.unidades),
            "operadores": len(self.operadores),
            "rutas": len(self.rutas),
            "tarifas": len(self.tarifas),
        }
