"""svc-ap — cuentas por pagar, calendario y prioridad de pago (§6.2).

El espejo de `svc-ar` del lado de lo que se paga, y la misma regla detrás de cada salida:

* **Vencido.** Un abono parcial reduce el saldo; **no** rejuvenece la cuenta. Lo mismo que
  `svc-ar`, en la dirección contraria.
* **Prioridad.** La calcula una rúbrica versionada, no el criterio de quien tenga la chequera
  a la mano (§9.1). A qué proveedor se le paga primero tiene efecto sobre la relación
  comercial y tiene que explicarse con los mismos números para todos.
* **Calendario.** Lo que aún no vence, agrupado por semana — lo que `svc-treasury` necesita
  para proyectar el flujo hacia adelante.

Lo que este servicio **no** hace: no paga, no reprograma y no condona. Ejecutar el pago es
`ACT-PAY`, y `ACT-PAY` no existe hasta `D2-05` en la Fase 4, con doble factor y `CTL-HITL` por
regla dura de `authority-gate.yaml`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from services.common.errors import ErrorDeValidacion
from services.common.money import cantidad, mxn, no_negativo

RAIZ = Path(__file__).resolve().parent.parent.parent
RUBRICA_POR_DEFECTO = RAIZ / "registry" / "policies" / "rubrica-pagos.yaml"


@dataclass(frozen=True)
class CuentaPorPagar:
    cuenta_id: str
    proveedor_id: str
    fecha_emision: date
    dias_credito: int
    total_mxn: Decimal
    concepto: str = ""

    def vence(self) -> date:
        return self.fecha_emision + timedelta(days=int(self.dias_credito))


@dataclass(frozen=True)
class PagoRealizado:
    fecha: date
    monto_mxn: Decimal
    referencia: str = ""
    cuenta_id: str = ""

    @property
    def identificado(self) -> bool:
        return bool(self.cuenta_id.strip())


@dataclass
class SaldoPorPagar:
    cuenta: CuentaPorPagar
    pagado_mxn: Decimal = Decimal("0.00")

    @property
    def saldo_mxn(self) -> Decimal:
        return mxn(self.cuenta.total_mxn - self.pagado_mxn)

    @property
    def liquidada(self) -> bool:
        return self.saldo_mxn <= 0

    @property
    def vencimiento(self) -> date:
        return self.cuenta.vence()

    def dias_vencido(self, corte: date) -> int:
        return max((corte - self.vencimiento).days, 0)

    def as_dict(self, corte: date) -> dict[str, object]:
        return {
            "cuenta_id": self.cuenta.cuenta_id,
            "proveedor_id": self.cuenta.proveedor_id,
            "total_mxn": str(self.cuenta.total_mxn),
            "pagado_mxn": str(self.pagado_mxn),
            "saldo_mxn": str(self.saldo_mxn),
            "vencimiento": self.vencimiento.isoformat(),
            "dias_vencido": self.dias_vencido(corte),
        }


@dataclass
class ConciliacionPagos:
    """Lo aplicado y —sobre todo— lo que no se pudo aplicar."""

    saldos: dict[str, SaldoPorPagar] = field(default_factory=dict)
    sin_identificar: list[PagoRealizado] = field(default_factory=list)
    sobrantes: list[tuple[str, Decimal]] = field(default_factory=list)

    @property
    def monto_sin_identificar(self) -> Decimal:
        return mxn(sum((p.monto_mxn for p in self.sin_identificar), Decimal("0")))


@dataclass(frozen=True)
class Tramo:
    nombre: str
    desde: int | None
    hasta: int | None

    def contiene(self, dias: int) -> bool:
        if self.desde is not None and dias < self.desde:
            return False
        if self.hasta is not None and dias > self.hasta:
            return False
        return True


@dataclass(frozen=True)
class RubricaPagos:
    version: str
    calibrado: bool
    peso_saldo: Decimal
    peso_dia: Decimal
    peso_proveedor_critico: Decimal
    proveedores_criticos: tuple[str, ...]
    tramos: list[Tramo]

    def tramo_de(self, dias_vencido: int) -> str:
        for tramo in self.tramos:
            if tramo.contiene(dias_vencido):
                return tramo.nombre
        return "sin_tramo"


def cargar_rubrica(ruta: str | Path | None = None) -> RubricaPagos:
    destino = Path(ruta) if ruta else RUBRICA_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    pesos = datos.get("pesos") or {}
    tramos = [
        Tramo(nombre=str(t.get("nombre")), desde=t.get("desde"), hasta=t.get("hasta"))
        for t in (datos.get("tramos") or [])
    ]
    if not tramos:
        raise ErrorDeValidacion("la rubrica no declara tramos de vencido", campo="tramos")
    return RubricaPagos(
        version=str(datos.get("version") or "v0"),
        calibrado=bool(datos.get("calibrado")),
        peso_saldo=cantidad(pesos.get("saldo_por_pagar_mxn", 1)),
        peso_dia=cantidad(pesos.get("por_dia_vencido", 0)),
        peso_proveedor_critico=cantidad(pesos.get("proveedor_critico", 0)),
        proveedores_criticos=tuple(str(p) for p in (datos.get("proveedores_criticos") or [])),
        tramos=tramos,
    )


def conciliar(cuentas: list[CuentaPorPagar], pagos: list[PagoRealizado]) -> ConciliacionPagos:
    """Aplica pagos a cuentas. Lo que no se puede casar se reporta, no se reparte."""
    conciliacion = ConciliacionPagos()
    for cuenta in cuentas:
        conciliacion.saldos[cuenta.cuenta_id] = SaldoPorPagar(cuenta=cuenta)

    por_id = conciliacion.saldos
    for pago in pagos:
        no_negativo(pago.monto_mxn, campo="monto_mxn")
        destino = pago.cuenta_id.strip()
        if not destino:
            coincidencias = [cid for cid in por_id if cid and cid in pago.referencia]
            destino = coincidencias[0] if len(coincidencias) == 1 else ""
        if not destino or destino not in por_id:
            conciliacion.sin_identificar.append(pago)
            continue

        saldo = por_id[destino]
        aplicable = min(pago.monto_mxn, saldo.saldo_mxn)
        saldo.pagado_mxn = mxn(saldo.pagado_mxn + aplicable)
        if pago.monto_mxn > aplicable:
            conciliacion.sobrantes.append((destino, mxn(pago.monto_mxn - aplicable)))

    return conciliacion


@dataclass
class Pagos:
    corte: date
    rubrica_version: str
    rubrica_calibrada: bool
    vencido: dict[str, Decimal]
    calendario: dict[str, Decimal]
    prioridad: list[dict]
    saldo_total_mxn: Decimal
    saldo_vencido_mxn: Decimal
    sin_identificar_mxn: Decimal

    def as_dict(self) -> dict[str, object]:
        return {
            "corte": self.corte.isoformat(),
            "rubrica_version": self.rubrica_version,
            "rubrica_calibrada": self.rubrica_calibrada,
            "vencido": {k: str(v) for k, v in self.vencido.items()},
            "calendario": {k: str(v) for k, v in self.calendario.items()},
            "prioridad": self.prioridad,
            "saldo_total_mxn": str(self.saldo_total_mxn),
            "saldo_vencido_mxn": str(self.saldo_vencido_mxn),
            "sin_identificar_mxn": str(self.sin_identificar_mxn),
        }


def analizar(conciliacion: ConciliacionPagos, *, corte: date, rubrica: RubricaPagos | None = None) -> Pagos:
    """Vencido, calendario y prioridad de pago a una fecha de corte."""
    rubrica = rubrica or cargar_rubrica()
    vencido: dict[str, Decimal] = {t.nombre: Decimal("0.00") for t in rubrica.tramos}
    calendario: dict[str, Decimal] = {}
    prioridad: list[dict] = []
    saldo_total = Decimal("0.00")
    saldo_vencido = Decimal("0.00")

    for saldo in conciliacion.saldos.values():
        if saldo.liquidada:
            continue
        dias = saldo.dias_vencido(corte)
        saldo_total = mxn(saldo_total + saldo.saldo_mxn)

        if dias > 0:
            tramo = rubrica.tramo_de(dias)
            vencido[tramo] = mxn(vencido.get(tramo, Decimal("0")) + saldo.saldo_mxn)
            saldo_vencido = mxn(saldo_vencido + saldo.saldo_mxn)
            es_critico = saldo.cuenta.proveedor_id in rubrica.proveedores_criticos
            puntos = mxn(
                saldo.saldo_mxn * rubrica.peso_saldo
                + Decimal(dias) * rubrica.peso_dia
                + (rubrica.peso_proveedor_critico if es_critico else Decimal("0"))
            )
            prioridad.append(
                {
                    "cuenta_id": saldo.cuenta.cuenta_id,
                    "proveedor_id": saldo.cuenta.proveedor_id,
                    "saldo_mxn": str(saldo.saldo_mxn),
                    "dias_vencido": dias,
                    "tramo": tramo,
                    "puntos": str(puntos),
                    "proveedor_critico": es_critico,
                    "rubrica_version": rubrica.version,
                }
            )
        else:
            semana = saldo.vencimiento.strftime("%Y-W%V")
            calendario[semana] = mxn(calendario.get(semana, Decimal("0")) + saldo.saldo_mxn)

    prioridad.sort(key=lambda fila: (Decimal(fila["puntos"]), Decimal(fila["saldo_mxn"])), reverse=True)

    return Pagos(
        corte=corte,
        rubrica_version=rubrica.version,
        rubrica_calibrada=rubrica.calibrado,
        vencido=vencido,
        calendario=dict(sorted(calendario.items())),
        prioridad=prioridad,
        saldo_total_mxn=saldo_total,
        saldo_vencido_mxn=saldo_vencido,
        sin_identificar_mxn=conciliacion.monto_sin_identificar,
    )
