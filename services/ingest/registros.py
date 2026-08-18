"""Registros canonicos que produce svc-ingest.

Todo lo que entra (banco, tickets de diesel, GPS, CSV del ERP) sale con esta
forma. De aqui en adelante ningun servicio vuelve a ver un encabezado de
Excel ni una fecha en formato dudoso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

TipoMovimiento = Literal["ingreso", "egreso"]


@dataclass(frozen=True)
class MovimientoBancario:
    fecha: date
    concepto: str
    monto_mxn: Decimal  # positivo = ingreso, negativo = egreso
    cuenta: str
    referencia: str
    origen: str

    @property
    def tipo(self) -> TipoMovimiento:
        return "ingreso" if self.monto_mxn >= 0 else "egreso"

    @property
    def clave_dedupe(self) -> tuple:
        return (self.cuenta, self.fecha, self.referencia, self.monto_mxn, self.concepto)


@dataclass(frozen=True)
class CargaDiesel:
    ticket_id: str
    fecha: date
    unit_id: str
    litros: Decimal
    precio_mxn_litro: Decimal
    importe_mxn: Decimal
    odometro_km: Decimal | None
    estacion: str
    origen: str

    @property
    def clave_dedupe(self) -> tuple:
        return (self.ticket_id,)


@dataclass(frozen=True)
class RecorridoGPS:
    """Kilometros que el GPS dice que se recorrieron, por unidad y viaje.

    Existe para contrastarlos con los km de la ruta del catalogo. La diferencia
    entre lo planeado y lo recorrido es costo que hoy nadie mide.
    """

    unit_id: str
    trip_id: str | None
    fecha_inicio: date
    fecha_fin: date
    km_recorridos: Decimal
    puntos: int
    origen: str

    @property
    def clave_dedupe(self) -> tuple:
        return (self.unit_id, self.trip_id, self.fecha_inicio)


@dataclass(frozen=True)
class Viaje:
    """El viaje tal como lo registra el ERP. Unidad de analisis de la Fase 0."""

    trip_id: str
    route_id: str
    unit_id: str
    operador_id: str
    cliente_id: str
    fecha_inicio: date
    fecha_fin: date
    ingreso_facturado_mxn: Decimal
    km_recorridos: Decimal | None = None
    estatus: str = "cerrado"
    origen: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def clave_dedupe(self) -> tuple:
        return (self.trip_id,)

    @property
    def dias(self) -> int:
        return max((self.fecha_fin - self.fecha_inicio).days + 1, 1)
