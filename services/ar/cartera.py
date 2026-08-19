"""svc-ar — cartera, aging y prioridad de cobranza (§6.2).

Tres salidas y una regla de diseño detrás de cada una:

* **Aging.** Un pago parcial reduce el saldo; **no** rejuvenece la factura. Una factura de hace
  cien días con abono de ayer sigue siendo de hace cien días, y ése es el número que importa.
* **Prioridad.** La calcula una rúbrica versionada, no el criterio del momento (§9.1). A quién
  se le cobra primero tiene efecto comercial y tiene que explicarse con los mismos números
  para todos.
* **Flujo esperado.** Es lo que se espera cobrar, no lo que ya se cobró. Contar dos veces el
  mismo peso es la forma más rápida de que una proyección de caja deje de creerse.

Lo que este servicio **no** hace: no condona, no reestructura y no manda un solo mensaje. La
gestión sale por plantilla fija de `svc-notify` y la ordena `D2-04`, con su gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from services.common.errors import ErrorDeValidacion
from services.common.money import cantidad, mxn, no_negativo
from services.masterdata.catalogo import Catalogo

RAIZ = Path(__file__).resolve().parent.parent.parent
RUBRICA_POR_DEFECTO = RAIZ / "registry" / "policies" / "rubrica-cobranza.yaml"


@dataclass(frozen=True)
class Factura:
    factura_id: str
    cliente_id: str
    fecha_emision: date
    total_mxn: Decimal
    trip_id: str = ""
    moneda: str = "MXN"

    def vence(self, dias_credito: int) -> date:
        return self.fecha_emision + timedelta(days=int(dias_credito))


@dataclass(frozen=True)
class Pago:
    fecha: date
    monto_mxn: Decimal
    referencia: str = ""
    factura_id: str = ""

    @property
    def identificado(self) -> bool:
        return bool(self.factura_id.strip())


@dataclass
class Saldo:
    factura: Factura
    dias_credito: int
    cobrado_mxn: Decimal = Decimal("0.00")

    @property
    def saldo_mxn(self) -> Decimal:
        return mxn(self.factura.total_mxn - self.cobrado_mxn)

    @property
    def liquidada(self) -> bool:
        return self.saldo_mxn <= 0

    @property
    def vencimiento(self) -> date:
        return self.factura.vence(self.dias_credito)

    def dias_vencido(self, corte: date) -> int:
        return max((corte - self.vencimiento).days, 0)

    def as_dict(self, corte: date) -> dict[str, object]:
        return {
            "factura_id": self.factura.factura_id,
            "cliente_id": self.factura.cliente_id,
            "total_mxn": str(self.factura.total_mxn),
            "cobrado_mxn": str(self.cobrado_mxn),
            "saldo_mxn": str(self.saldo_mxn),
            "vencimiento": self.vencimiento.isoformat(),
            "dias_vencido": self.dias_vencido(corte),
        }


@dataclass
class Conciliacion:
    """Lo aplicado y —sobre todo— lo que no se pudo aplicar."""

    saldos: dict[str, Saldo] = field(default_factory=dict)
    sin_identificar: list[Pago] = field(default_factory=list)
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
class Rubrica:
    version: str
    calibrado: bool
    peso_saldo: Decimal
    peso_dia: Decimal
    peso_sin_credito: Decimal
    tramos: list[Tramo]
    dias_gestion_humana: int
    dias_direccion: int

    def tramo_de(self, dias_vencido: int) -> str:
        for tramo in self.tramos:
            if tramo.contiene(dias_vencido):
                return tramo.nombre
        return "sin_tramo"


def cargar_rubrica(ruta: str | Path | None = None) -> Rubrica:
    destino = Path(ruta) if ruta else RUBRICA_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    pesos = datos.get("pesos") or {}
    escalamiento = datos.get("escalamiento") or {}
    tramos = [
        Tramo(nombre=str(t.get("nombre")), desde=t.get("desde"), hasta=t.get("hasta"))
        for t in (datos.get("tramos") or [])
    ]
    if not tramos:
        raise ErrorDeValidacion("la rubrica no declara tramos de aging", campo="tramos")
    return Rubrica(
        version=str(datos.get("version") or "v0"),
        calibrado=bool(datos.get("calibrado")),
        peso_saldo=cantidad(pesos.get("saldo_vencido_mxn", 1)),
        peso_dia=cantidad(pesos.get("por_dia_vencido", 0)),
        peso_sin_credito=cantidad(pesos.get("cliente_sin_credito", 0)),
        tramos=tramos,
        dias_gestion_humana=int(escalamiento.get("dias_para_gestion_humana", 15)),
        dias_direccion=int(escalamiento.get("dias_para_direccion", 60)),
    )


def conciliar(facturas: list[Factura], pagos: list[Pago], catalogo: Catalogo) -> Conciliacion:
    """Aplica pagos a facturas. Lo que no se puede casar se reporta, no se reparte.

    Repartir un depósito sin referencia entre las facturas más viejas es lo que hace una hoja
    de cálculo y es la razón por la que la cartera nunca cuadra: el saldo se ve bien y el
    cliente reclama una factura que "ya pagó". Aquí un pago sin identificar queda a la vista.
    """
    conciliacion = Conciliacion()
    for factura in facturas:
        cliente = catalogo.cliente(factura.cliente_id)
        conciliacion.saldos[factura.factura_id] = Saldo(
            factura=factura,
            dias_credito=int(cliente.dias_credito),
        )

    por_id = conciliacion.saldos
    for pago in pagos:
        no_negativo(pago.monto_mxn, campo="monto_mxn")
        destino = pago.factura_id.strip()
        if not destino:
            # Segundo intento, y el último: la referencia bancaria a veces trae el folio.
            coincidencias = [fid for fid in por_id if fid and fid in pago.referencia]
            destino = coincidencias[0] if len(coincidencias) == 1 else ""
        if not destino or destino not in por_id:
            conciliacion.sin_identificar.append(pago)
            continue

        saldo = por_id[destino]
        aplicable = min(pago.monto_mxn, saldo.saldo_mxn)
        saldo.cobrado_mxn = mxn(saldo.cobrado_mxn + aplicable)
        if pago.monto_mxn > aplicable:
            conciliacion.sobrantes.append((destino, mxn(pago.monto_mxn - aplicable)))

    return conciliacion


@dataclass
class Cartera:
    corte: date
    rubrica_version: str
    rubrica_calibrada: bool
    aging: dict[str, Decimal]
    por_cliente: dict[str, dict[str, Decimal]]
    prioridad: list[dict]
    saldo_total_mxn: Decimal
    saldo_vencido_mxn: Decimal
    sin_identificar_mxn: Decimal
    dias_cartera: Decimal | None = None
    flujo_esperado: dict[str, Decimal] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "corte": self.corte.isoformat(),
            "rubrica_version": self.rubrica_version,
            "rubrica_calibrada": self.rubrica_calibrada,
            "aging": {k: str(v) for k, v in self.aging.items()},
            "por_cliente": {c: {k: str(v) for k, v in t.items()} for c, t in self.por_cliente.items()},
            "prioridad": self.prioridad,
            "saldo_total_mxn": str(self.saldo_total_mxn),
            "saldo_vencido_mxn": str(self.saldo_vencido_mxn),
            "sin_identificar_mxn": str(self.sin_identificar_mxn),
            "dias_cartera": str(self.dias_cartera) if self.dias_cartera is not None else None,
            "flujo_esperado": {k: str(v) for k, v in self.flujo_esperado.items()},
        }


def analizar(
    conciliacion: Conciliacion,
    *,
    corte: date,
    rubrica: Rubrica | None = None,
    ventas_del_periodo_mxn: Decimal | None = None,
    dias_del_periodo: int = 30,
) -> Cartera:
    """Aging, prioridad y flujo esperado a una fecha de corte."""
    rubrica = rubrica or cargar_rubrica()
    aging: dict[str, Decimal] = {t.nombre: Decimal("0.00") for t in rubrica.tramos}
    por_cliente: dict[str, dict[str, Decimal]] = {}
    prioridad: list[dict] = []
    flujo: dict[str, Decimal] = {}
    saldo_total = Decimal("0.00")
    saldo_vencido = Decimal("0.00")

    for saldo in conciliacion.saldos.values():
        if saldo.liquidada:
            continue
        dias = saldo.dias_vencido(corte)
        tramo = rubrica.tramo_de(dias)
        aging[tramo] = mxn(aging.get(tramo, Decimal("0")) + saldo.saldo_mxn)
        cliente = por_cliente.setdefault(saldo.factura.cliente_id, {t.nombre: Decimal("0.00") for t in rubrica.tramos})
        cliente[tramo] = mxn(cliente.get(tramo, Decimal("0")) + saldo.saldo_mxn)
        saldo_total = mxn(saldo_total + saldo.saldo_mxn)

        if dias > 0:
            saldo_vencido = mxn(saldo_vencido + saldo.saldo_mxn)
            puntos = mxn(
                saldo.saldo_mxn * rubrica.peso_saldo
                + Decimal(dias) * rubrica.peso_dia
                + (rubrica.peso_sin_credito if saldo.dias_credito == 0 else Decimal("0"))
            )
            prioridad.append(
                {
                    "factura_id": saldo.factura.factura_id,
                    "cliente_id": saldo.factura.cliente_id,
                    "saldo_mxn": str(saldo.saldo_mxn),
                    "dias_vencido": dias,
                    "tramo": tramo,
                    "puntos": str(puntos),
                    "accion": _accion(dias, rubrica),
                    "rubrica_version": rubrica.version,
                }
            )
        else:
            # Lo que aún no vence es flujo esperado, agrupado por la semana en que cae.
            semana = saldo.vencimiento.strftime("%Y-W%V")
            flujo[semana] = mxn(flujo.get(semana, Decimal("0")) + saldo.saldo_mxn)

    prioridad.sort(key=lambda fila: (Decimal(fila["puntos"]), Decimal(fila["saldo_mxn"])), reverse=True)

    dias_cartera = None
    if ventas_del_periodo_mxn and ventas_del_periodo_mxn > 0:
        dias_cartera = (saldo_total / mxn(ventas_del_periodo_mxn) * Decimal(dias_del_periodo)).quantize(Decimal("0.1"))

    return Cartera(
        corte=corte,
        rubrica_version=rubrica.version,
        rubrica_calibrada=rubrica.calibrado,
        aging=aging,
        por_cliente=por_cliente,
        prioridad=prioridad,
        saldo_total_mxn=saldo_total,
        saldo_vencido_mxn=saldo_vencido,
        sin_identificar_mxn=conciliacion.monto_sin_identificar,
        dias_cartera=dias_cartera,
        flujo_esperado=dict(sorted(flujo.items())),
    )


def _accion(dias_vencido: int, rubrica: Rubrica) -> str:
    """Qué toca hacer. El servicio propone el escalón; ejecutarlo es de D2-04, con su gate."""
    if dias_vencido >= rubrica.dias_direccion:
        return "direccion"
    if dias_vencido >= rubrica.dias_gestion_humana:
        return "gestion_humana"
    return "recordatorio_por_plantilla"
