"""Cartera a partir de lo que ya normalizó la Fase 0.

`svc-ingest` deja los viajes del ERP y los movimientos del banco en forma canónica. Con eso se
puede armar la cartera sin capturar nada dos veces:

    viaje cerrado con ingreso facturado ─► factura
    abono en el banco                   ─► pago

Es una aproximación **declarada**, no un atajo escondido: mientras el ERP no emita el
comprobante (eso llega con `svc-invoicing` en producción), la factura de un viaje se deduce de
su ingreso. Las dos deducciones que hace esta función están en `SUPUESTOS` y viajan en la
salida, porque de ellas depende que el aging signifique algo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from services.ar.cartera import Cartera, Factura, Pago, Rubrica, analizar, conciliar
from services.ingest.normalizador import normalizar_banco, normalizar_viajes
from services.masterdata.catalogo import Catalogo
from services.masterdata.loader import cargar_catalogo, leer_csv

SUPUESTOS = (
    "La factura de un viaje se deduce de su ingreso facturado y se fecha el dia de cierre: "
    "el ERP todavia no emite el comprobante.",
    "Todo abono del banco es cobro de cliente. Sin referencia que lo ligue a una factura, "
    "queda como pago sin identificar y no se reparte.",
)


@dataclass
class CarteraDeOperacion:
    cartera: Cartera
    facturas: list[Factura]
    pagos: list[Pago]
    supuestos: tuple[str, ...] = SUPUESTOS

    def as_dict(self) -> dict[str, object]:
        return {
            **self.cartera.as_dict(),
            "facturas": len(self.facturas),
            "pagos": len(self.pagos),
            "supuestos": list(self.supuestos),
        }


def construir(
    datos: str | Path,
    *,
    corte: date | None = None,
    catalogo: Catalogo | None = None,
    rubrica: Rubrica | None = None,
) -> CarteraDeOperacion:
    """Arma la cartera desde `data/<lo que sea>/` con la misma forma que la Fase 0."""
    raiz = Path(datos)
    catalogo = catalogo or cargar_catalogo(raiz / "catalogo")

    viajes = normalizar_viajes(leer_csv(raiz / "operacion" / "viajes.csv"), catalogo=catalogo)
    banco = normalizar_banco(leer_csv(raiz / "operacion" / "banco.csv"))

    facturas = [
        Factura(
            factura_id=f"F-{viaje.trip_id}",
            cliente_id=viaje.cliente_id,
            fecha_emision=viaje.fecha_fin,
            total_mxn=viaje.ingreso_facturado_mxn,
            trip_id=viaje.trip_id,
        )
        for viaje in viajes.registros
        if viaje.estatus == "cerrado" and viaje.ingreso_facturado_mxn > 0
    ]

    pagos = [
        Pago(fecha=movimiento.fecha, monto_mxn=movimiento.monto_mxn, referencia=movimiento.referencia)
        for movimiento in banco.registros
        if movimiento.tipo == "ingreso"
    ]

    ventas = sum((f.total_mxn for f in facturas), Decimal("0"))
    conciliacion = conciliar(facturas, pagos, catalogo)
    cartera = analizar(
        conciliacion,
        corte=corte or date.today(),
        rubrica=rubrica,
        ventas_del_periodo_mxn=ventas if ventas > 0 else None,
        dias_del_periodo=30,
    )
    return CarteraDeOperacion(cartera=cartera, facturas=facturas, pagos=pagos)
