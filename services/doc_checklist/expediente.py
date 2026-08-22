"""svc-doc-checklist — completitud documental del viaje antes de facturar (§6.3).

La primera de las dos puertas del ciclo operación → ingreso. Responde tres preguntas y sólo
tres, todas verificables sin leer el contenido de un documento:

    ¿está?          presencia
    ¿sigue vigente? aritmética de fechas
    ¿es de este viaje? referencia

Lo que **no** hace, y es deliberado: no interpreta el documento. Si el POD está firmado por
quien no debía, eso lo ve una persona. Un servicio que empieza a juzgar contenido deja de ser
determinístico y pasa a ser un criterio, y un criterio no puede ser condición de facturación.

`expediente_completo` es un booleano duro y es entrada obligatoria de `svc-invoicing`: un viaje
sin POD no llega a tener borrador de factura. La condición se aplica donde se produce el objeto,
no en la revisión de quien lo recibe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from services.common.errors import ErrorDeServicio, ErrorDeValidacion
from services.masterdata.models import fecha as parse_fecha

RAIZ = Path(__file__).resolve().parent.parent.parent
CATALOGO_POR_DEFECTO = RAIZ / "registry" / "policies" / "requisitos-documentales.yaml"

FALTA = "falta"
VENCIDO = "vencido"
NO_APLICA = "no_aplica"


class ExpedienteIncompleto(ErrorDeServicio):
    """El viaje no reúne su expediente. No se factura, y se dice qué falta."""

    codigo = "DOCS-INCOMPLETO"


class TipoDeServicioDesconocido(ErrorDeServicio):
    """El catálogo no declara qué documentos exige ese tipo de servicio."""

    codigo = "DOCS-SERVICIO-DESCONOCIDO"


@dataclass(frozen=True)
class Documento:
    """Un documento del expediente. El archivo no vive aquí: vive su referencia."""

    tipo: str
    trip_id: str
    folio: str = ""
    emitido: date | None = None
    vence: date | None = None
    referencia: str = ""      # ruta, URL o hash del archivo; lo decide el ERP
    origen: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "tipo": self.tipo,
            "trip_id": self.trip_id,
            "folio": self.folio,
            "emitido": self.emitido.isoformat() if self.emitido else None,
            "vence": self.vence.isoformat() if self.vence else None,
            "referencia": self.referencia,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Documento":
        return cls(
            tipo=str(datos.get("tipo") or "").strip(),
            trip_id=str(datos.get("trip_id") or "").strip(),
            folio=str(datos.get("folio") or "").strip(),
            emitido=parse_fecha(datos["emitido"], campo="emitido") if datos.get("emitido") else None,
            vence=parse_fecha(datos["vence"], campo="vence") if datos.get("vence") else None,
            referencia=str(datos.get("referencia") or "").strip(),
            origen=str(datos.get("origen") or "").strip(),
        )


@dataclass(frozen=True)
class Requisito:
    tipo: str
    obligatorio: bool
    nombre: str = ""
    vigencia_dias: int | None = None


@dataclass(frozen=True)
class Faltante:
    """Un requisito incumplido, con el motivo separado del hecho.

    "Falta el POD" y "el POD venció" mandan a la misma persona a hacer cosas distintas.
    """

    tipo: str
    motivo: str
    obligatorio: bool
    detalle: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "tipo": self.tipo,
            "motivo": self.motivo,
            "obligatorio": self.obligatorio,
            "detalle": self.detalle,
        }


@dataclass(frozen=True)
class CatalogoDocumental:
    """Los requisitos por tipo de servicio, tal como los aprueba la operación."""

    version: str
    confirmado: bool
    tipos: dict[str, dict]
    servicios: dict[str, list[Requisito]]
    respaldo_de_concepto: dict[str, str] = field(default_factory=dict)

    def requisitos(self, tipo_de_servicio: str) -> list[Requisito]:
        if tipo_de_servicio not in self.servicios:
            raise TipoDeServicioDesconocido(
                f"el catalogo {self.version} no declara requisitos para {tipo_de_servicio!r}; "
                f"declarados: {', '.join(sorted(self.servicios)) or 'ninguno'}",
                campo="tipo_de_servicio",
            )
        return self.servicios[tipo_de_servicio]

    def documento_que_respalda(self, concepto: str) -> str | None:
        return self.respaldo_de_concepto.get(concepto)


def cargar_catalogo_documental(ruta: str | Path | None = None) -> CatalogoDocumental:
    destino = Path(ruta) if ruta else CATALOGO_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    tipos = dict(datos.get("tipos") or {})

    servicios: dict[str, list[Requisito]] = {}
    for servicio, requisitos in (datos.get("servicios") or {}).items():
        lista: list[Requisito] = []
        for crudo in requisitos or []:
            tipo = str(crudo.get("tipo") or "").strip()
            if tipo not in tipos:
                raise ErrorDeValidacion(
                    f"{servicio} exige {tipo!r}, que no esta declarado en `tipos`", campo="tipo"
                )
            definicion = tipos[tipo] or {}
            lista.append(
                Requisito(
                    tipo=tipo,
                    obligatorio=bool(crudo.get("obligatorio", True)),
                    nombre=str(definicion.get("nombre") or tipo),
                    vigencia_dias=definicion.get("vigencia_dias"),
                )
            )
        servicios[str(servicio)] = lista

    return CatalogoDocumental(
        version=str(datos.get("version") or "v0"),
        confirmado=bool(datos.get("confirmado")),
        tipos=tipos,
        servicios=servicios,
        respaldo_de_concepto=dict(datos.get("respaldo_de_concepto") or {}),
    )


@dataclass
class Expediente:
    """El dictamen documental de un viaje. Lo consume svc-invoicing como condición dura."""

    trip_id: str
    tipo_de_servicio: str
    fecha_corte: date
    catalogo_version: str
    catalogo_confirmado: bool
    presentes: list[Documento] = field(default_factory=list)
    faltantes: list[Faltante] = field(default_factory=list)
    vencidos: list[Faltante] = field(default_factory=list)
    no_corresponden: list[Documento] = field(default_factory=list)

    @property
    def bloqueantes(self) -> list[Faltante]:
        return [f for f in self.faltantes + self.vencidos if f.obligatorio]

    @property
    def completo(self) -> bool:
        return not self.bloqueantes

    @property
    def listo_para_facturar(self) -> bool:
        return self.completo

    def tiene(self, tipo: str) -> bool:
        return any(d.tipo == tipo for d in self.presentes)

    def as_dict(self) -> dict[str, object]:
        return {
            "trip_id": self.trip_id,
            "tipo_de_servicio": self.tipo_de_servicio,
            "fecha_corte": self.fecha_corte.isoformat(),
            "catalogo_version": self.catalogo_version,
            "catalogo_confirmado": self.catalogo_confirmado,
            "completo": self.completo,
            "listo_para_facturar": self.listo_para_facturar,
            "presentes": [d.as_dict() for d in self.presentes],
            "faltantes": [f.as_dict() for f in self.faltantes],
            "vencidos": [f.as_dict() for f in self.vencidos],
            "no_corresponden": [d.as_dict() for d in self.no_corresponden],
        }


def _vencido(documento: Documento, requisito: Requisito, corte: date) -> bool:
    """Vence por fecha explícita o por vigencia derivada de la emisión, en ese orden.

    La fecha explícita gana siempre: si el documento dice cuándo vence, no hay nada que
    deducir. La vigencia por días es el respaldo para los documentos que no la traen impresa.
    """
    if documento.vence is not None:
        return documento.vence < corte
    if requisito.vigencia_dias and documento.emitido is not None:
        return documento.emitido + timedelta(days=int(requisito.vigencia_dias)) < corte
    return False


def revisar(
    *,
    trip_id: str,
    tipo_de_servicio: str,
    documentos: list[Documento],
    catalogo: CatalogoDocumental | None = None,
    fecha_corte: date | None = None,
) -> Expediente:
    """Arma el expediente del viaje. No falla por incompleto: lo reporta.

    Levantar aquí sería cómodo y sería un error: quien pregunta "¿qué falta?" necesita la
    lista, no una excepción. El bloqueo vive en `exigir_completo` y en `svc-invoicing`.
    """
    catalogo = catalogo or cargar_catalogo_documental()
    corte = fecha_corte or date.today()
    requisitos = catalogo.requisitos(tipo_de_servicio)

    expediente = Expediente(
        trip_id=trip_id,
        tipo_de_servicio=tipo_de_servicio,
        fecha_corte=corte,
        catalogo_version=catalogo.version,
        catalogo_confirmado=catalogo.confirmado,
    )

    # Un documento de otro viaje no es un documento de este viaje. Suena obvio y es la forma
    # más común de que un expediente se vea completo sin estarlo: se adjunta el POD anterior.
    del_viaje: list[Documento] = []
    for documento in documentos:
        if documento.trip_id and documento.trip_id != trip_id:
            expediente.no_corresponden.append(documento)
        else:
            del_viaje.append(documento)

    exigidos = {r.tipo for r in requisitos}
    for documento in del_viaje:
        if documento.tipo not in exigidos:
            expediente.no_corresponden.append(documento)

    for requisito in requisitos:
        candidatos = [d for d in del_viaje if d.tipo == requisito.tipo]
        if not candidatos:
            expediente.faltantes.append(
                Faltante(
                    tipo=requisito.tipo,
                    motivo=FALTA,
                    obligatorio=requisito.obligatorio,
                    detalle=requisito.nombre,
                )
            )
            continue

        vigentes = [d for d in candidatos if not _vencido(d, requisito, corte)]
        if vigentes:
            expediente.presentes.extend(vigentes)
            continue

        # Está, y no cuenta. Se reporta como vencido —no como faltante— porque lo que hay
        # que hacer es renovarlo, no buscarlo.
        expediente.vencidos.append(
            Faltante(
                tipo=requisito.tipo,
                motivo=VENCIDO,
                obligatorio=requisito.obligatorio,
                detalle=f"{requisito.nombre}: vencido al {corte.isoformat()}",
            )
        )

    return expediente


def exigir_completo(expediente: Expediente) -> Expediente:
    """La puerta. `svc-invoicing` la cruza antes de armar nada."""
    if expediente.completo:
        return expediente
    detalle = "; ".join(f"{f.tipo} ({f.motivo})" for f in expediente.bloqueantes)
    raise ExpedienteIncompleto(
        f"el viaje {expediente.trip_id} no se puede facturar: {detalle}",
        campo="expediente",
        trip_id=expediente.trip_id,
        faltantes=[f.as_dict() for f in expediente.bloqueantes],
    )


def concepto_respaldado(expediente: Expediente, concepto: str, catalogo: CatalogoDocumental) -> bool:
    """¿Hay documento que soporte cobrar este concepto?

    Una estadía que nadie firmó no se cobra; una estadía firmada no se pierde. El segundo
    caso es el más común y el más caro: es dinero trabajado que se cae por no adjuntar papel.
    """
    requerido = catalogo.documento_que_respalda(concepto)
    if requerido is None:
        return True
    return expediente.tiene(requerido)
