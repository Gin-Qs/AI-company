"""svc-pricing - tarifa = svc-costing + margen objetivo + política de descuento.

Dos cosas que este servicio **no** hace, y que definen su diseño:

* **No inventa la tabla de precios.** Gabriel la fija por ruta y la actualiza cada mes; aquí se
  consume como dato maestro (§17.2). Lo que el sistema añade es contrastar el margen mínimo que
  la tabla promete contra el que la operación entrega.
* **No deja que un LLM calcule el precio.** El §4.1 lo dice del agente `D4-03`: "no calcula el
  precio. El gate de margen mínimo es determinístico: una cotización bajo el umbral **no puede
  generarse**, no depende de que el LLM lo note".

Esa última frase es literal en el código: `cotizar()` levanta antes de devolver nada. La única
forma de emitir por debajo del mínimo es con una autorización de Dirección explícita, que queda
registrada en la cotización.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import yaml

from services.common.errors import EntradaFaltante, ErrorDeServicio, ErrorDeValidacion
from services.common.money import cantidad, cuota, mxn
from services.common.result import Autorizacion, Supuesto
from services.costing.motor import EntradaCosteo, ResultadoCosteo, costear
from services.masterdata.catalogo import Catalogo
from services.masterdata.models import Tarifa
from services.trace.libro import Libro
from services.validation.reglas import Dictamen, validar

RAIZ = Path(__file__).resolve().parent.parent.parent
GATE = RAIZ / "registry" / "policies" / "authority-gate.yaml"

CENTAVO = Decimal("0.01")

AGENTE = "agente"
HUMANO = "humano_operativo"
DIRECCION = "direccion"


class CotizacionBloqueada(ErrorDeServicio):
    """El gate no permite generar esta cotización. No es un aviso: es un bloqueo."""

    codigo = "PRICING-BLOQUEADA"


class SinTarifaVigente(ErrorDeServicio):
    """No hay renglón de la tabla pre-aprobada para esa ruta, cliente y fecha."""

    codigo = "PRICING-SIN-TARIFA"


@dataclass(frozen=True)
class PoliticaCotizacion:
    """Lo que el Gate de Autoridad dice sobre cotizar y descontar (§11.4)."""

    descuento_max_operativo_pct: Decimal
    quien_operativo: str
    quien_direccion: str
    margen_objetivo_pct: Decimal | None
    margen_minimo_pct: Decimal | None
    calibrado: bool
    version: str = "v1"

    @property
    def objetivo_calibrado(self) -> bool:
        return self.margen_objetivo_pct is not None


def cargar_politica(ruta: str | Path | None = None) -> PoliticaCotizacion:
    destino = Path(ruta) if ruta else GATE
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    umbrales = datos.get("umbrales") or {}
    cotizacion = umbrales.get("cotizacion") or {}
    descuento = umbrales.get("descuento_tarifa") or {}

    objetivo = cotizacion.get("margen_objetivo_pct")
    minimo = cotizacion.get("margen_minimo_pct")
    return PoliticaCotizacion(
        descuento_max_operativo_pct=cantidad(
            (descuento.get("humano_operativo") or {}).get("max_pct", 5), campo="descuento_max_pct"
        ),
        quien_operativo=str((cotizacion.get("humano_operativo") or {}).get("quien") or "humano operativo"),
        quien_direccion=str((cotizacion.get("direccion") or {}).get("quien") or "Direccion"),
        margen_objetivo_pct=cuota(objetivo) if objetivo is not None else None,
        margen_minimo_pct=cuota(minimo) if minimo is not None else None,
        calibrado=bool(cotizacion.get("calibrado")),
        version=str(datos.get("version") or "v1"),
    )


@dataclass
class EntradaCotizacion:
    route_id: str
    unit_id: str
    cliente_id: str
    operador_id: str | None = None
    fecha: date | None = None
    km: Decimal | None = None
    fuel_price: Decimal | None = None
    descuento_pct: Decimal | None = None
    precio_propuesto_mxn: Decimal | None = None
    trace_id: str = ""


@dataclass
class Cotizacion:
    route_id: str
    cliente_id: str
    unit_id: str
    fecha: str
    precio_mxn: Decimal
    precio_tabla_mxn: Decimal
    costo_mxn: Decimal
    costo_por_km: Decimal
    margen_mxn: Decimal
    margen_pct: Decimal
    margen_minimo_pct: Decimal
    descuento_pct: Decimal
    nivel_autorizacion: str
    quien_autoriza: str
    tarifa_id: str
    dentro_de_tabla: bool
    motivo_gate: str
    autorizacion: Autorizacion | None = None
    assumptions: list[Supuesto] = field(default_factory=list)
    cifras: dict[str, str] = field(default_factory=dict)
    fuentes: dict[str, str] = field(default_factory=dict)
    costeo: ResultadoCosteo | None = None

    @property
    def requiere_humano(self) -> bool:
        return self.nivel_autorizacion != AGENTE

    def as_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "cliente_id": self.cliente_id,
            "unit_id": self.unit_id,
            "fecha": self.fecha,
            "precio_mxn": str(self.precio_mxn),
            "precio_tabla_mxn": str(self.precio_tabla_mxn),
            "costo_mxn": str(self.costo_mxn),
            "costo_por_km": str(self.costo_por_km),
            "margen_mxn": str(self.margen_mxn),
            "margen_pct": str(self.margen_pct),
            "margen_minimo_pct": str(self.margen_minimo_pct),
            "descuento_pct": str(self.descuento_pct),
            "nivel_autorizacion": self.nivel_autorizacion,
            "quien_autoriza": self.quien_autoriza,
            "tarifa_id": self.tarifa_id,
            "dentro_de_tabla": self.dentro_de_tabla,
            "motivo_gate": self.motivo_gate,
            "autorizacion": self.autorizacion.as_dict() if self.autorizacion else None,
            "assumptions": [s.as_dict() for s in self.assumptions],
            "cifras": self.cifras,
            "fuentes": self.fuentes,
        }

    def para_validar(self, politica: PoliticaCotizacion) -> dict[str, object]:
        return {
            "margen_pct": self.margen_pct,
            "margen_minimo_pct": self.margen_minimo_pct,
            "descuento_pct": self.descuento_pct,
            "descuento_max_pct": politica.descuento_max_operativo_pct,
            "precio_mxn": self.precio_mxn,
            "costo_mxn": self.costo_mxn,
        }


def cotizar(
    entrada: EntradaCotizacion,
    catalogo: Catalogo,
    *,
    politica: PoliticaCotizacion | None = None,
    autorizacion: Autorizacion | None = None,
    libro: Libro | None = None,
) -> Cotizacion:
    """Calcula la cotización y aplica el gate. Determinística de punta a punta."""
    politica = politica or cargar_politica()
    dia = entrada.fecha or date.today()
    unidad = catalogo.unidad(entrada.unit_id)

    tarifa = catalogo.tarifa_vigente(
        entrada.route_id, dia, cliente_id=entrada.cliente_id, tipo_unidad=unidad.tipo
    )
    if tarifa is None:
        raise SinTarifaVigente(
            f"no hay tarifa pre-aprobada para {entrada.route_id} / {entrada.cliente_id} al {dia.isoformat()}: "
            f"cotizar fuera de tabla lo autoriza {politica.quien_direccion}",
            campo="tarifa",
            route_id=entrada.route_id,
        )

    minimo = _margen_minimo(tarifa, politica)
    costeo = costear(
        EntradaCosteo(
            route_id=entrada.route_id,
            unit_id=entrada.unit_id,
            operador_id=entrada.operador_id,
            fuel_price=entrada.fuel_price,
            km=entrada.km,
            fecha=dia,
        ),
        catalogo,
    )

    precio, descuento = _precio_y_descuento(entrada, tarifa)
    if precio <= 0:
        raise ErrorDeValidacion("precio no positivo", campo="precio_mxn")

    margen_mxn = mxn(precio - costeo.total_trip_cost)
    margen_pct = ((margen_mxn / precio) * 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    dentro_de_tabla = descuento == 0 and precio == tarifa.precio_mxn

    nivel, quien, motivo = _gate(
        margen_pct=margen_pct,
        minimo=minimo,
        descuento=descuento,
        dentro_de_tabla=dentro_de_tabla,
        politica=politica,
    )

    # El bloqueo duro: por debajo del mínimo no se genera. Ni con buena redacción.
    if margen_pct < minimo and autorizacion is None:
        raise CotizacionBloqueada(
            f"margen {margen_pct}% por debajo del mínimo {minimo}% de la ruta {entrada.route_id}: "
            f"la cotización no puede generarse sin autorización de {politica.quien_direccion}",
            campo="margen_pct",
            margen_pct=str(margen_pct),
            margen_minimo_pct=str(minimo),
            requiere=politica.quien_direccion,
        )

    cotizacion = Cotizacion(
        route_id=entrada.route_id,
        cliente_id=entrada.cliente_id,
        unit_id=entrada.unit_id,
        fecha=dia.isoformat(),
        precio_mxn=precio,
        precio_tabla_mxn=tarifa.precio_mxn,
        costo_mxn=costeo.total_trip_cost,
        costo_por_km=costeo.cost_per_km,
        margen_mxn=margen_mxn,
        margen_pct=margen_pct,
        margen_minimo_pct=minimo,
        descuento_pct=descuento,
        nivel_autorizacion=nivel,
        quien_autoriza=quien,
        tarifa_id=tarifa.tarifa_id,
        dentro_de_tabla=dentro_de_tabla,
        motivo_gate=motivo,
        autorizacion=autorizacion,
        assumptions=list(costeo.assumptions),
        costeo=costeo,
    )

    if libro is not None:
        _registrar_cifras(cotizacion, libro, tarifa)
    return cotizacion


def dictaminar(cotizacion: Cotizacion, politica: PoliticaCotizacion | None = None) -> Dictamen:
    """Pasa la cotización por svc-validation. Se llama antes de entregarla a nadie."""
    politica = politica or cargar_politica()
    return validar(cotizacion.para_validar(politica), "cotizacion")


def precio_para_margen(costo: Decimal, margen_pct: Decimal) -> Decimal:
    """Precio que deja exactamente ese margen sobre el precio (no sobre el costo)."""
    objetivo = cantidad(margen_pct, campo="margen_pct")
    if not (Decimal(0) <= objetivo < Decimal(100)):
        raise ErrorDeValidacion(f"margen objetivo fuera de [0, 100): {objetivo}", campo="margen_pct")
    return mxn(cantidad(costo) / (1 - objetivo / 100))


# --- interno --------------------------------------------------------------


def _margen_minimo(tarifa: Tarifa, politica: PoliticaCotizacion) -> Decimal:
    """El mínimo sale de la tabla; el umbral global es el respaldo. Si faltan los dos, no se cotiza."""
    if tarifa.margen_minimo_pct is not None:
        return tarifa.margen_minimo_pct.quantize(CENTAVO)
    if politica.margen_minimo_pct is not None:
        return politica.margen_minimo_pct.quantize(CENTAVO)
    raise EntradaFaltante(
        f"la tarifa {tarifa.tarifa_id} no declara margen mínimo y el umbral global sigue sin calibrar "
        f"(docs/umbrales.md): sin mínimo no hay gate, y sin gate no se cotiza",
        campo="margen_minimo_pct",
        tarifa_id=tarifa.tarifa_id,
    )


def _precio_y_descuento(entrada: EntradaCotizacion, tarifa: Tarifa) -> tuple[Decimal, Decimal]:
    if entrada.precio_propuesto_mxn is not None and entrada.descuento_pct is not None:
        raise ErrorDeValidacion(
            "se recibieron precio propuesto y descuento a la vez: son dos formas de decir lo mismo",
            campo="precio_propuesto_mxn",
        )

    if entrada.precio_propuesto_mxn is not None:
        precio = mxn(entrada.precio_propuesto_mxn, campo="precio_propuesto_mxn")
        descuento = ((tarifa.precio_mxn - precio) / tarifa.precio_mxn * 100).quantize(CENTAVO)
        return precio, max(descuento, Decimal("0.00"))

    descuento = cantidad(entrada.descuento_pct or 0, campo="descuento_pct").quantize(CENTAVO)
    if descuento < 0:
        raise ErrorDeValidacion("descuento negativo: eso es un recargo, y no se cotiza así", campo="descuento_pct")
    if descuento >= 100:
        raise ErrorDeValidacion("descuento de 100% o más", campo="descuento_pct")
    return mxn(tarifa.precio_mxn * (1 - descuento / 100)), descuento


def _gate(
    *,
    margen_pct: Decimal,
    minimo: Decimal,
    descuento: Decimal,
    dentro_de_tabla: bool,
    politica: PoliticaCotizacion,
) -> tuple[str, str, str]:
    """Quién tiene que autorizar. El texto de authority-gate.yaml, hecho código."""
    if margen_pct < minimo:
        return DIRECCION, politica.quien_direccion, f"margen {margen_pct}% bajo el mínimo {minimo}% de la ruta"

    if descuento > politica.descuento_max_operativo_pct:
        return (
            DIRECCION,
            politica.quien_direccion,
            f"descuento {descuento}% sobre el máximo operativo de {politica.descuento_max_operativo_pct}%",
        )

    if not dentro_de_tabla:
        return (
            HUMANO,
            politica.quien_operativo,
            f"dentro de tabla pero con negociación: descuento {descuento}%",
        )

    if politica.objetivo_calibrado and margen_pct < politica.margen_objetivo_pct:
        return (
            HUMANO,
            politica.quien_operativo,
            f"margen {margen_pct}% entre el mínimo {minimo}% y el objetivo {politica.margen_objetivo_pct}%",
        )

    # authority-gate.yaml, cotizacion.agente_solo:
    # "tarifa dentro de la tabla vigente y margen >= minimo de la ruta"
    return AGENTE, "agente", f"tarifa de tabla y margen {margen_pct}% sobre el mínimo {minimo}%"


def _registrar_cifras(cotizacion: Cotizacion, libro: Libro, tarifa: Tarifa) -> None:
    """Deja cada número con su origen, para que svc-trace pueda reconciliar el entregable."""
    registros = (
        ("precio", cotizacion.precio_mxn, "svc-pricing", f"tarifa {tarifa.tarifa_id} {tarifa.version}", "MXN"),
        ("costo", cotizacion.costo_mxn, "svc-costing", f"costeo de {cotizacion.route_id}/{cotizacion.unit_id}", "MXN"),
        ("costo_por_km", cotizacion.costo_por_km, "svc-costing", f"costo por km de {cotizacion.route_id}", "MXN/km"),
        ("margen", cotizacion.margen_mxn, "svc-pricing", "precio - costo total", "MXN"),
        ("margen_pct", cotizacion.margen_pct, "svc-pricing", "margen / precio", "pct"),
        ("margen_minimo_pct", cotizacion.margen_minimo_pct, "svc-masterdata", f"tabla de precios {tarifa.tarifa_id}", "pct"),
    )
    for nombre, valor, servicio, consulta, unidad in registros:
        cifra = libro.registrar(nombre, valor, servicio=servicio, consulta=consulta, unidad=unidad)
        cotizacion.cifras[nombre] = str(valor)
        cotizacion.fuentes[nombre] = cifra.cifra_id
