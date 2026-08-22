"""svc-treasury — posición de caja, flujo proyectado y días de caja (§6.2).

Tres salidas y la misma regla detrás de las tres: **este servicio no mueve un peso, sólo
cuenta lo que otros ya movieron o ya calcularon que se va a mover.**

* **Posición diaria.** Corre el saldo día a día sobre los movimientos bancarios que ya
  normalizó `svc-ingest` desde la Fase 0. No hay un segundo libro de caja.
* **Flujo proyectado.** Suma lo que `svc-ar` ya calculó que se va a cobrar y resta lo que
  `svc-ap` ya calculó que se va a pagar. Si alguno de los dos cambia su número, el flujo
  proyectado cambia solo — no hay una copia local que se pueda desincronizar.
* **Días de caja.** El saldo actual contra el gasto diario promedio de los últimos días. Sin
  gasto histórico el resultado es indeterminado, no infinito: una caja que nunca ha gastado no
  es una caja que "aguanta para siempre".

Lo que este servicio **no** hace: no ejecuta pagos ni transferencias, y no inventa un saldo
inicial — lo recibe declarado, porque no hay integración bancaria que lo lea de la cuenta real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from services.common.money import mxn, no_negativo
from services.ingest.registros import MovimientoBancario


@dataclass(frozen=True)
class MovimientoDiario:
    fecha: date
    ingresos_mxn: Decimal
    egresos_mxn: Decimal
    saldo_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "fecha": self.fecha.isoformat(),
            "ingresos_mxn": str(self.ingresos_mxn),
            "egresos_mxn": str(self.egresos_mxn),
            "saldo_mxn": str(self.saldo_mxn),
        }


@dataclass
class Tesoreria:
    corte: date
    saldo_actual_mxn: Decimal
    posicion_diaria: list[MovimientoDiario]
    flujo_semanal: dict[str, Decimal]
    gasto_diario_promedio_mxn: Decimal
    dias_de_caja: Decimal | None
    assumptions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "corte": self.corte.isoformat(),
            "saldo_actual_mxn": str(self.saldo_actual_mxn),
            "posicion_diaria": [m.as_dict() for m in self.posicion_diaria],
            "flujo_semanal": {k: str(v) for k, v in self.flujo_semanal.items()},
            "gasto_diario_promedio_mxn": str(self.gasto_diario_promedio_mxn),
            "dias_de_caja": str(self.dias_de_caja) if self.dias_de_caja is not None else None,
            "assumptions": list(self.assumptions),
        }


def posicion_diaria(
    movimientos: list[MovimientoBancario], *, saldo_inicial_mxn: object, corte: date
) -> tuple[list[MovimientoDiario], Decimal]:
    """Corre el saldo día a día sobre los movimientos hasta el corte, inclusive."""
    saldo = no_negativo(mxn(saldo_inicial_mxn, campo="saldo_inicial_mxn"), campo="saldo_inicial_mxn")

    por_dia: dict[date, list[MovimientoBancario]] = {}
    for movimiento in movimientos:
        if movimiento.fecha > corte:
            continue
        por_dia.setdefault(movimiento.fecha, []).append(movimiento)

    resultado: list[MovimientoDiario] = []
    for dia in sorted(por_dia):
        ingresos = mxn(sum((m.monto_mxn for m in por_dia[dia] if m.monto_mxn > 0), Decimal("0")))
        egresos = mxn(sum((-m.monto_mxn for m in por_dia[dia] if m.monto_mxn < 0), Decimal("0")))
        saldo = mxn(saldo + ingresos - egresos)
        resultado.append(MovimientoDiario(fecha=dia, ingresos_mxn=ingresos, egresos_mxn=egresos, saldo_mxn=saldo))

    return resultado, saldo


def gasto_diario_promedio(
    movimientos: list[MovimientoBancario], *, corte: date, dias_historial: int = 30
) -> Decimal:
    """Egresos de los últimos `dias_historial` días, entre esos mismos días.

    Se divide entre el tamaño de la ventana, no entre los días con movimiento: un solo egreso
    grande hace diez días atrás no puede verse como "gasto diario" de hoy.
    """
    desde = corte - timedelta(days=dias_historial)
    egresos = [-m.monto_mxn for m in movimientos if desde < m.fecha <= corte and m.monto_mxn < 0]
    if not egresos:
        return Decimal("0.00")
    total = mxn(sum(egresos, Decimal("0")))
    return mxn(total / dias_historial)


def dias_de_caja(saldo_actual_mxn: Decimal, gasto_diario_promedio_mxn: Decimal) -> Decimal | None:
    """Saldo contra gasto diario promedio. Sin gasto histórico, `None` — no infinito."""
    if gasto_diario_promedio_mxn <= 0:
        return None
    return (saldo_actual_mxn / gasto_diario_promedio_mxn).quantize(Decimal("0.1"))


def flujo_proyectado(
    saldo_actual_mxn: Decimal,
    flujo_esperado_cobros: dict[str, Decimal],
    calendario_pagos: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Saldo semana a semana: lo que `svc-ar` espera cobrar menos lo que `svc-ap` va a pagar."""
    semanas = sorted(set(flujo_esperado_cobros) | set(calendario_pagos))
    resultado: dict[str, Decimal] = {}
    saldo = saldo_actual_mxn
    for semana in semanas:
        cobros = mxn(flujo_esperado_cobros.get(semana, Decimal("0")))
        pagos = mxn(calendario_pagos.get(semana, Decimal("0")))
        saldo = mxn(saldo + cobros - pagos)
        resultado[semana] = saldo
    return resultado


def construir(
    movimientos: list[MovimientoBancario],
    *,
    saldo_inicial_mxn: object,
    corte: date,
    flujo_esperado_cobros: dict[str, Decimal] | None = None,
    calendario_pagos: dict[str, Decimal] | None = None,
    dias_historial: int = 30,
) -> Tesoreria:
    """Arma la posición de caja completa: diaria, proyectada y días de caja."""
    diaria, saldo_actual = posicion_diaria(movimientos, saldo_inicial_mxn=saldo_inicial_mxn, corte=corte)
    gasto = gasto_diario_promedio(movimientos, corte=corte, dias_historial=dias_historial)
    dias = dias_de_caja(saldo_actual, gasto)
    semanal = flujo_proyectado(saldo_actual, flujo_esperado_cobros or {}, calendario_pagos or {})

    assumptions = [
        f"saldo inicial declarado: $ {mxn(saldo_inicial_mxn)} — sin integración bancaria que lo confirme"
    ]
    if dias is None:
        assumptions.append(
            f"sin egresos en los últimos {dias_historial} días: dias_de_caja no se puede calcular, "
            "no es infinito"
        )

    return Tesoreria(
        corte=corte,
        saldo_actual_mxn=saldo_actual,
        posicion_diaria=diaria,
        flujo_semanal=semanal,
        gasto_diario_promedio_mxn=gasto,
        dias_de_caja=dias,
        assumptions=assumptions,
    )
