"""svc-invoicing — emisión y timbrado (§6.2).

Es el hueco más caro de la v1: la operación cerraba viajes y el ingreso se facturaba a mano.
El servicio arma el comprobante a partir del viaje cerrado y su expediente, y se detiene justo
antes de la única parte que no le corresponde.

Tres reglas duras, en este orden:

1. **Sin expediente completo no hay borrador.** No es una advertencia al final: `armar_borrador`
   cruza la puerta de `svc-doc-checklist` antes de calcular un solo importe.
2. **Un concepto sin documento que lo respalde no se cobra.** Una estadía que nadie firmó no se
   factura; una estadía firmada no se pierde. El segundo caso es el más común y el más caro.
3. **Timbrar es `ACT-DOC-S`, y `ACT-DOC-S` es HITL siempre** (§11.4). No hay monto que lo exente
   y no hay forma de llamar a `timbrar()` sin una autorización humana explícita.

El folio es un recurso, no un número: se reserva en un libro append-only. Dos facturas con el
mismo folio no es un bug estético — es un problema fiscal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml

from services.common.errors import EntradaFaltante, ErrorDeServicio, ErrorDeValidacion
from services.common.money import mxn, no_negativo, positivo
from services.common.result import Autorizacion, Supuestos
from services.doc_checklist.expediente import (
    CatalogoDocumental,
    Expediente,
    cargar_catalogo_documental,
    concepto_respaldado,
    exigir_completo,
)
from services.masterdata.catalogo import Catalogo
from services.masterdata.models import Cliente

RAIZ = Path(__file__).resolve().parent.parent.parent
POLITICA_POR_DEFECTO = RAIZ / "registry" / "policies" / "facturacion.yaml"
LIBRO_POR_DEFECTO = RAIZ / "data" / "facturacion" / "folios.jsonl"

CENTAVO = Decimal("0.01")


class ConceptoSinRespaldo(ErrorDeServicio):
    """Se intentó facturar algo que ningún documento del expediente soporta."""

    codigo = "INV-SIN-RESPALDO"


class ViajeYaFacturado(ErrorDeServicio):
    """Ese viaje ya tiene comprobante. Refacturar es un proceso distinto, con reglas del SAT."""

    codigo = "INV-YA-FACTURADO"


class TimbradoRequiereHumano(ErrorDeServicio):
    """ACT-DOC-S es CTL-HITL siempre. El servicio no timbra solo, por diseño."""

    codigo = "INV-TIMBRADO-HITL"


@dataclass(frozen=True)
class PoliticaFacturacion:
    version: str
    confirmado: bool
    serie_por_defecto: str
    iva_pct: Decimal
    retencion_pct: Decimal
    conceptos: dict[str, dict]
    quien_timbra: str
    pac: str | None
    estado_sin_pac: str

    def clave_de(self, tipo: str) -> dict:
        if tipo not in self.conceptos:
            raise ErrorDeValidacion(
                f"tipo de concepto desconocido: {tipo!r}; declarados: {', '.join(sorted(self.conceptos))}",
                campo="tipo",
            )
        return self.conceptos[tipo]


def cargar_politica(ruta: str | Path | None = None) -> PoliticaFacturacion:
    destino = Path(ruta) if ruta else POLITICA_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    impuestos = datos.get("impuestos") or {}
    timbrado = datos.get("timbrado") or {}
    return PoliticaFacturacion(
        version=str(datos.get("version") or "v0"),
        confirmado=bool(datos.get("confirmado")),
        serie_por_defecto=str(datos.get("serie_por_defecto") or "A"),
        iva_pct=mxn(impuestos.get("iva_pct", 16)),
        retencion_pct=mxn(impuestos.get("retencion_iva_autotransporte_pct", 0)),
        conceptos=dict(datos.get("conceptos") or {}),
        quien_timbra=str(timbrado.get("quien_timbra") or "Direccion"),
        pac=timbrado.get("pac"),
        estado_sin_pac=str(timbrado.get("estado_sin_pac") or "pendiente_pac"),
    )


@dataclass(frozen=True)
class Concepto:
    """Una línea del comprobante. `tipo` es de negocio; las claves son del SAT."""

    tipo: str                       # flete | demora | estadia | maniobra
    descripcion: str
    cantidad: Decimal
    valor_unitario_mxn: Decimal
    clave_prod_serv: str = ""
    clave_unidad: str = ""

    @property
    def importe_mxn(self) -> Decimal:
        return mxn(self.cantidad * self.valor_unitario_mxn)

    def as_dict(self) -> dict[str, object]:
        return {
            "tipo": self.tipo,
            "descripcion": self.descripcion,
            "cantidad": str(self.cantidad),
            "valor_unitario_mxn": str(self.valor_unitario_mxn),
            "importe_mxn": str(self.importe_mxn),
            "clave_prod_serv": self.clave_prod_serv,
            "clave_unidad": self.clave_unidad,
        }


class LibroDeFolios:
    """Folios emitidos, append-only. Un folio entregado no se devuelve ni se reescribe."""

    def __init__(self, archivo: str | Path | None = None) -> None:
        self.archivo = Path(archivo) if archivo else LIBRO_POR_DEFECTO

    def _asientos(self) -> list[dict]:
        if not self.archivo.is_file():
            return []
        return [json.loads(l) for l in self.archivo.read_text(encoding="utf-8").splitlines() if l.strip()]

    def _escribir(self, asiento: dict) -> None:
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        with self.archivo.open("a", encoding="utf-8") as destino:
            destino.write(json.dumps(asiento, ensure_ascii=False) + "\n")

    def siguiente_folio(self, serie: str) -> int:
        usados = [int(a["folio"]) for a in self._asientos() if a.get("serie") == serie]
        return max(usados, default=0) + 1

    def facturado(self, trip_id: str) -> dict | None:
        for asiento in self._asientos():
            if asiento.get("trip_id") == trip_id:
                return asiento
        return None

    def reservar(self, *, serie: str, trip_id: str, cliente_id: str, total_mxn: Decimal) -> int:
        ya = self.facturado(trip_id)
        if ya:
            raise ViajeYaFacturado(
                f"el viaje {trip_id} ya tiene el comprobante {ya['serie']}-{ya['folio']}",
                campo="trip_id",
                serie=ya["serie"],
                folio=ya["folio"],
            )
        folio = self.siguiente_folio(serie)
        self._escribir(
            {
                "evento": "reserva",
                "serie": serie,
                "folio": folio,
                "trip_id": trip_id,
                "cliente_id": cliente_id,
                "total_mxn": str(total_mxn),
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        return folio

    def registrar_timbrado(self, *, serie: str, folio: int, estado: str, quien: str, motivo: str) -> None:
        self._escribir(
            {
                "evento": "timbrado",
                "serie": serie,
                "folio": folio,
                "estado": estado,
                "autorizo": quien,
                "motivo": motivo,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )


@dataclass
class EntradaFactura:
    trip_id: str
    cliente_id: str
    conceptos: list[Concepto]
    fecha: date | None = None
    serie: str | None = None
    trace_id: str = ""


@dataclass
class Borrador:
    """El comprobante armado y **sin timbrar**. Ese último paso es de una persona."""

    serie: str
    folio: int
    trip_id: str
    cliente_id: str
    receptor_rfc: str
    fecha: date
    conceptos: list[Concepto]
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    retencion_mxn: Decimal
    total_mxn: Decimal
    politica_version: str
    politica_confirmada: bool
    expediente_version: str
    assumptions: list = field(default_factory=list)
    estado: str = "borrador"
    trace_id: str = ""

    @property
    def identificador(self) -> str:
        return f"{self.serie}-{self.folio}"

    @property
    def requiere_hitl(self) -> bool:
        # No es una propiedad calculada: es una constante con nombre. ACT-DOC-S siempre.
        return True

    @property
    def cifras(self) -> dict[str, Decimal]:
        """Lo que svc-trace registra de este comprobante."""
        return {
            "subtotal": self.subtotal_mxn,
            "iva": self.iva_mxn,
            "retencion": self.retencion_mxn,
            "total": self.total_mxn,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "comprobante": self.identificador,
            "trip_id": self.trip_id,
            "cliente_id": self.cliente_id,
            "receptor_rfc": self.receptor_rfc,
            "fecha": self.fecha.isoformat(),
            "conceptos": [c.as_dict() for c in self.conceptos],
            "subtotal_mxn": str(self.subtotal_mxn),
            "iva_mxn": str(self.iva_mxn),
            "retencion_mxn": str(self.retencion_mxn),
            "total_mxn": str(self.total_mxn),
            "estado": self.estado,
            "requiere_hitl": self.requiere_hitl,
            "politica_version": self.politica_version,
            "politica_confirmada": self.politica_confirmada,
            "supuestos": [s.as_dict() for s in self.assumptions],
        }


@dataclass(frozen=True)
class Timbrado:
    serie: str
    folio: int
    estado: str
    autorizo: str
    motivo: str
    uuid: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "comprobante": f"{self.serie}-{self.folio}",
            "estado": self.estado,
            "autorizo": self.autorizo,
            "motivo": self.motivo,
            "uuid": self.uuid,
        }


def es_persona_moral(rfc: str) -> bool:
    """12 posiciones = moral, 13 = física. Es deducción del sistema, no dato capturado.

    Se declara como supuesto en el borrador porque de esto depende la retención del 4%, y una
    retención mal aplicada es una diferencia que aparece meses después en la conciliación.
    """
    return len(rfc.strip()) == 12


def conceptos_de_viaje(
    *,
    precio_flete_mxn: Decimal,
    demoras_horas: Decimal | None = None,
    tarifa_demora_mxn_hora: Decimal | None = None,
    estadias_dias: Decimal | None = None,
    tarifa_estadia_mxn_dia: Decimal | None = None,
    politica: PoliticaFacturacion | None = None,
) -> list[Concepto]:
    """Arma las líneas típicas de un viaje. Las demoras y estadías son ingreso, no un favor."""
    politica = politica or cargar_politica()
    lineas: list[Concepto] = []

    def linea(tipo: str, cantidad: Decimal, unitario: Decimal) -> Concepto:
        clave = politica.clave_de(tipo)
        return Concepto(
            tipo=tipo,
            descripcion=str(clave.get("descripcion") or tipo),
            cantidad=cantidad,
            valor_unitario_mxn=mxn(unitario),
            clave_prod_serv=str(clave.get("clave_prod_serv") or ""),
            clave_unidad=str(clave.get("clave_unidad") or ""),
        )

    lineas.append(linea("flete", Decimal("1"), positivo(mxn(precio_flete_mxn), campo="precio_flete_mxn")))
    if demoras_horas and tarifa_demora_mxn_hora:
        lineas.append(linea("demora", Decimal(str(demoras_horas)), mxn(tarifa_demora_mxn_hora)))
    if estadias_dias and tarifa_estadia_mxn_dia:
        lineas.append(linea("estadia", Decimal(str(estadias_dias)), mxn(tarifa_estadia_mxn_dia)))
    return lineas


def armar_borrador(
    entrada: EntradaFactura,
    catalogo: Catalogo,
    expediente: Expediente,
    *,
    politica: PoliticaFacturacion | None = None,
    catalogo_documental: CatalogoDocumental | None = None,
    libro: LibroDeFolios | None = None,
) -> Borrador:
    """Del viaje cerrado al comprobante, sin timbrar. Cruza las tres puertas antes de calcular."""
    politica = politica or cargar_politica()
    catalogo_documental = catalogo_documental or cargar_catalogo_documental()
    libro = libro or LibroDeFolios()
    supuestos = Supuestos()

    if expediente.trip_id != entrada.trip_id:
        raise ErrorDeValidacion(
            f"el expediente es del viaje {expediente.trip_id} y la factura del {entrada.trip_id}",
            campo="trip_id",
        )

    # Puerta 1: el expediente. Levanta antes de que exista un solo importe.
    exigir_completo(expediente)

    # Puerta 2: cada concepto, con el documento que lo respalda.
    if not entrada.conceptos:
        raise EntradaFaltante("una factura sin conceptos no es una factura", campo="conceptos")
    for concepto in entrada.conceptos:
        if not concepto_respaldado(expediente, concepto.tipo, catalogo_documental):
            requerido = catalogo_documental.documento_que_respalda(concepto.tipo)
            raise ConceptoSinRespaldo(
                f"no se puede cobrar {concepto.tipo} del viaje {entrada.trip_id}: "
                f"falta {requerido} en el expediente",
                campo="conceptos",
                concepto=concepto.tipo,
                requiere=requerido,
            )

    cliente: Cliente = catalogo.cliente(entrada.cliente_id)
    if not cliente.rfc:
        raise EntradaFaltante(
            f"el cliente {cliente.cliente_id} no tiene RFC en el catalogo: sin dato fiscal no hay comprobante",
            campo="rfc",
        )

    subtotal = mxn(sum((c.importe_mxn for c in entrada.conceptos), Decimal("0")))
    no_negativo(subtotal, campo="subtotal")

    iva = mxn(subtotal * politica.iva_pct / Decimal(100))
    supuestos.registrar("iva_pct", politica.iva_pct, "parametro", f"politica de facturacion {politica.version}")

    moral = es_persona_moral(cliente.rfc)
    retencion = mxn(subtotal * politica.retencion_pct / Decimal(100)) if moral else Decimal("0.00")
    supuestos.registrar(
        "retencion_iva_pct",
        politica.retencion_pct if moral else Decimal("0"),
        "derivado",
        f"RFC {cliente.rfc} de {len(cliente.rfc)} posiciones: "
        + ("persona moral, retiene 4% de autotransporte" if moral else "persona fisica, no retiene"),
    )

    total = mxn(subtotal + iva - retencion)
    serie = entrada.serie or politica.serie_por_defecto

    # Puerta 3: el folio. Reservar es lo último — si algo falla arriba, no se quema un folio.
    folio = libro.reservar(serie=serie, trip_id=entrada.trip_id, cliente_id=cliente.cliente_id, total_mxn=total)

    return Borrador(
        serie=serie,
        folio=folio,
        trip_id=entrada.trip_id,
        cliente_id=cliente.cliente_id,
        receptor_rfc=cliente.rfc,
        fecha=entrada.fecha or date.today(),
        conceptos=list(entrada.conceptos),
        subtotal_mxn=subtotal,
        iva_mxn=iva,
        retencion_mxn=retencion,
        total_mxn=total,
        politica_version=politica.version,
        politica_confirmada=politica.confirmado,
        expediente_version=expediente.catalogo_version,
        assumptions=list(supuestos),
        trace_id=entrada.trace_id,
    )


def timbrar(
    borrador: Borrador,
    *,
    autorizacion: Autorizacion | None = None,
    politica: PoliticaFacturacion | None = None,
    libro: LibroDeFolios | None = None,
) -> Timbrado:
    """Timbra el comprobante. Sin autorización humana explícita, levanta — siempre.

    No hay parámetro que desactive esta condición y no debe haberlo: el día que exista, la
    regla dura de §11.4 pasa a depender de que nadie lo use.
    """
    politica = politica or cargar_politica()
    libro = libro or LibroDeFolios()

    if autorizacion is None or not autorizacion.quien.strip():
        raise TimbradoRequiereHumano(
            f"{borrador.identificador} no se timbra solo: ACT-DOC-S es CTL-HITL siempre. "
            f"Autoriza {politica.quien_timbra}",
            campo="autorizacion",
            comprobante=borrador.identificador,
            requiere=politica.quien_timbra,
        )

    # Sin PAC contratado el sistema no puede timbrar de verdad, y no lo finge: deja el
    # comprobante autorizado y en espera. Devolver un UUID inventado seria mucho peor que
    # devolver "pendiente".
    estado = politica.estado_sin_pac if not politica.pac else "timbrado"
    borrador.estado = estado
    libro.registrar_timbrado(
        serie=borrador.serie,
        folio=borrador.folio,
        estado=estado,
        quien=autorizacion.quien,
        motivo=autorizacion.motivo,
    )
    return Timbrado(
        serie=borrador.serie,
        folio=borrador.folio,
        estado=estado,
        autorizo=autorizacion.quien,
        motivo=autorizacion.motivo,
    )
