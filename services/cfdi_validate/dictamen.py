"""svc-cfdi-validate — validación de CFDI y Carta Porte (§6.2).

La arquitectura es explícita sobre este servicio: *"un LLM aquí sólo añade riesgo"*. Es un
dominio donde acertar el 95% de las veces no sirve de nada — el SAT rechaza el 5% restante y
la factura no existe. Por eso todo aquí son reglas nombradas, con código estable y severidad.

**Qué valida y qué no, dicho sin adornos:**

* Valida **estructura** (los elementos y atributos que el comprobante debe traer),
  **catálogo** (que cada clave exista en el subconjunto versionado que Fleeter usa) y
  **aritmética** (que las sumas cuadren al centavo).
* **No sustituye la validación XSD del SAT.** Los XSD no viven en este repositorio. Antes de
  timbrar de verdad hay que pasar el XML por el esquema oficial; este servicio atrapa antes lo
  que se puede atrapar sin él, que resulta ser la mayoría de los rechazos reales.

Eso está declarado en el contrato del servicio y en `catalogos-sat.yaml`. Un validador que se
presenta como más completo de lo que es sería peor que no tenerlo: daría permiso para no mirar.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from services.common.errors import ErrorDeServicio
from services.common.money import mxn
from services.validation.reglas import Dictamen, Hallazgo

RAIZ = Path(__file__).resolve().parent.parent.parent
CATALOGOS_POR_DEFECTO = RAIZ / "registry" / "policies" / "catalogos-sat.yaml"

CENTAVO = Decimal("0.01")


class XMLIlegible(ErrorDeServicio):
    """El texto no es XML. No es un hallazgo del comprobante: no hay comprobante que mirar."""

    codigo = "CFDI-XML-ILEGIBLE"


@dataclass(frozen=True)
class CatalogosSAT:
    version: str
    completo: bool
    cfdi: dict
    carta_porte: dict

    def claves(self, grupo: str, seccion: str = "cfdi") -> set[str]:
        origen = self.cfdi if seccion == "cfdi" else self.carta_porte
        valores = origen.get(grupo) or {}
        return set(valores) if isinstance(valores, dict) else set(str(v) for v in valores)


def cargar_catalogos(ruta: str | Path | None = None) -> CatalogosSAT:
    destino = Path(ruta) if ruta else CATALOGOS_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    return CatalogosSAT(
        version=str(datos.get("version") or "v0"),
        completo=bool(datos.get("completo")),
        cfdi=dict(datos.get("cfdi") or {}),
        carta_porte=dict(datos.get("carta_porte") or {}),
    )


@dataclass
class DictamenCFDI:
    """El dictamen y **con qué versión de catálogo se produjo**.

    Sin esa versión el dictamen no se puede repetir: dentro de seis meses nadie sabría contra
    qué se validó, y "pasó la validación" dejaría de significar algo.
    """

    dictamen: Dictamen
    catalogo_version: str
    catalogo_completo: bool
    cfdi_version: str = ""
    con_carta_porte: bool = False

    @property
    def ok(self) -> bool:
        return self.dictamen.ok

    @property
    def hallazgos(self) -> list[Hallazgo]:
        return self.dictamen.hallazgos

    @property
    def errores(self) -> list[Hallazgo]:
        return self.dictamen.errores

    def as_dict(self) -> dict[str, object]:
        return {
            **self.dictamen.as_dict(),
            "catalogo_version": self.catalogo_version,
            "catalogo_completo": self.catalogo_completo,
            "cfdi_version": self.cfdi_version,
            "con_carta_porte": self.con_carta_porte,
            "valida_xsd": False,   # explícito: este servicio no reemplaza el esquema oficial
        }


def _local(etiqueta: str) -> str:
    """Nombre del elemento sin su namespace. El CFDI trae tres o cuatro namespaces distintos."""
    return etiqueta.rsplit("}", 1)[-1]


def _hijo(nodo: ET.Element | None, nombre: str) -> ET.Element | None:
    if nodo is None:
        return None
    for hijo in nodo:
        if _local(hijo.tag) == nombre:
            return hijo
    return None


def _hijos(nodo: ET.Element | None, nombre: str) -> list[ET.Element]:
    if nodo is None:
        return []
    return [h for h in nodo if _local(h.tag) == nombre]


def _buscar(nodo: ET.Element, nombre: str) -> ET.Element | None:
    for elemento in nodo.iter():
        if _local(elemento.tag) == nombre:
            return elemento
    return None


def _decimal(valor: str | None) -> Decimal | None:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


# Atributos obligatorios del nodo raíz. No es el XSD: es el subconjunto que, faltando,
# garantiza rechazo — y que además se puede comprobar sin descargar nada.
OBLIGATORIOS_COMPROBANTE = ("Version", "Fecha", "Moneda", "TipoDeComprobante", "SubTotal", "Total")
OBLIGATORIOS_EMISOR = ("Rfc", "Nombre", "RegimenFiscal")
OBLIGATORIOS_RECEPTOR = ("Rfc", "Nombre", "UsoCFDI", "DomicilioFiscalReceptor", "RegimenFiscalReceptor")
OBLIGATORIOS_CONCEPTO = ("ClaveProdServ", "ClaveUnidad", "Cantidad", "Descripcion", "ValorUnitario", "Importe")


def validar_cfdi(
    xml_texto: str,
    *,
    catalogos: CatalogosSAT | None = None,
    rfc_receptor_esperado: str | None = None,
    exige_carta_porte: bool = False,
) -> DictamenCFDI:
    """Dictamina un CFDI. Nunca corrige, nunca timbra y nunca opina de fiscal."""
    catalogos = catalogos or cargar_catalogos()
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError as exc:
        raise XMLIlegible(f"el XML no se puede parsear: {exc}", campo="xml") from exc

    hallazgos: list[Hallazgo] = []

    def error(regla: str, campo: str, mensaje: str) -> None:
        hallazgos.append(Hallazgo(regla=regla, campo=campo, mensaje=mensaje))

    def aviso(regla: str, campo: str, mensaje: str) -> None:
        hallazgos.append(Hallazgo(regla=regla, campo=campo, mensaje=mensaje, severidad="advertencia"))

    if _local(raiz.tag) != "Comprobante":
        error("CFDI-001", "raiz", f"el nodo raiz es {_local(raiz.tag)!r} y debe ser Comprobante")
        return DictamenCFDI(
            dictamen=Dictamen(ambito="cfdi", hallazgos=hallazgos),
            catalogo_version=catalogos.version,
            catalogo_completo=catalogos.completo,
        )

    # --- estructura ------------------------------------------------------
    for atributo in OBLIGATORIOS_COMPROBANTE:
        if not raiz.get(atributo):
            error("CFDI-002", f"Comprobante@{atributo}", "atributo obligatorio ausente o vacio")

    version = raiz.get("Version", "")
    aceptadas = [str(v) for v in (catalogos.cfdi.get("versiones_aceptadas") or [])]
    if version and aceptadas and version not in aceptadas:
        error("CFDI-003", "Comprobante@Version", f"version {version} fuera de las aceptadas: {', '.join(aceptadas)}")

    emisor = _hijo(raiz, "Emisor")
    receptor = _hijo(raiz, "Receptor")
    conceptos_nodo = _hijo(raiz, "Conceptos")
    conceptos = _hijos(conceptos_nodo, "Concepto")

    if emisor is None:
        error("CFDI-004", "Emisor", "el comprobante no trae Emisor")
    else:
        for atributo in OBLIGATORIOS_EMISOR:
            if not emisor.get(atributo):
                error("CFDI-004", f"Emisor@{atributo}", "atributo obligatorio ausente o vacio")

    if receptor is None:
        error("CFDI-005", "Receptor", "el comprobante no trae Receptor")
    else:
        for atributo in OBLIGATORIOS_RECEPTOR:
            if not receptor.get(atributo):
                error("CFDI-005", f"Receptor@{atributo}", "atributo obligatorio ausente o vacio")

    if not conceptos:
        error("CFDI-006", "Conceptos", "el comprobante no trae ningun Concepto")

    # --- catálogo --------------------------------------------------------
    def en_catalogo(valor: str | None, grupo: str, campo: str, regla: str, seccion: str = "cfdi") -> None:
        permitidas = catalogos.claves(grupo, seccion)
        if valor and permitidas and valor not in permitidas:
            error(regla, campo, f"{valor!r} no esta en el catalogo {grupo} ({catalogos.version})")

    en_catalogo(raiz.get("TipoDeComprobante"), "tipos_comprobante", "Comprobante@TipoDeComprobante", "CFDI-010")
    en_catalogo(raiz.get("Moneda"), "monedas", "Comprobante@Moneda", "CFDI-011")
    en_catalogo(raiz.get("FormaPago"), "formas_pago", "Comprobante@FormaPago", "CFDI-012")
    en_catalogo(raiz.get("MetodoPago"), "metodos_pago", "Comprobante@MetodoPago", "CFDI-013")
    if emisor is not None:
        en_catalogo(emisor.get("RegimenFiscal"), "regimenes_fiscales", "Emisor@RegimenFiscal", "CFDI-014")
    if receptor is not None:
        en_catalogo(receptor.get("UsoCFDI"), "usos_cfdi", "Receptor@UsoCFDI", "CFDI-015")
        en_catalogo(
            receptor.get("RegimenFiscalReceptor"),
            "regimenes_fiscales",
            "Receptor@RegimenFiscalReceptor",
            "CFDI-016",
        )

    for indice, concepto in enumerate(conceptos, start=1):
        for atributo in OBLIGATORIOS_CONCEPTO:
            if not concepto.get(atributo):
                error("CFDI-006", f"Concepto[{indice}]@{atributo}", "atributo obligatorio ausente o vacio")
        en_catalogo(concepto.get("ClaveProdServ"), "claves_prod_serv", f"Concepto[{indice}]@ClaveProdServ", "CFDI-017")
        en_catalogo(concepto.get("ClaveUnidad"), "claves_unidad", f"Concepto[{indice}]@ClaveUnidad", "CFDI-018")

    # --- aritmética ------------------------------------------------------
    subtotal = _decimal(raiz.get("SubTotal"))
    total = _decimal(raiz.get("Total"))
    descuento = _decimal(raiz.get("Descuento")) or Decimal("0")

    suma_conceptos = Decimal("0")
    for indice, concepto in enumerate(conceptos, start=1):
        importe = _decimal(concepto.get("Importe"))
        cantidad = _decimal(concepto.get("Cantidad"))
        unitario = _decimal(concepto.get("ValorUnitario"))
        if importe is None:
            continue
        suma_conceptos += importe
        if cantidad is not None and unitario is not None and mxn(cantidad * unitario) != mxn(importe):
            error(
                "CFDI-020",
                f"Concepto[{indice}]@Importe",
                f"{importe} no es cantidad x valor unitario ({mxn(cantidad * unitario)})",
            )

    if subtotal is not None and conceptos and mxn(suma_conceptos) != mxn(subtotal):
        error("CFDI-021", "Comprobante@SubTotal", f"{subtotal} no cuadra con la suma de conceptos ({mxn(suma_conceptos)})")

    traslados = Decimal("0")
    retenciones = Decimal("0")
    impuestos = _hijo(raiz, "Impuestos")
    if impuestos is not None:
        traslados = _decimal(impuestos.get("TotalImpuestosTrasladados")) or Decimal("0")
        retenciones = _decimal(impuestos.get("TotalImpuestosRetenidos")) or Decimal("0")

    if subtotal is not None and total is not None:
        esperado = mxn(subtotal - descuento + traslados - retenciones)
        if esperado != mxn(total):
            error(
                "CFDI-022",
                "Comprobante@Total",
                f"{total} no cuadra: subtotal - descuento + traslados - retenciones = {esperado}",
            )

    # --- receptor contra el viaje ---------------------------------------
    if rfc_receptor_esperado and receptor is not None:
        emitido = (receptor.get("Rfc") or "").strip().upper()
        esperado_rfc = rfc_receptor_esperado.strip().upper()
        if emitido and emitido != esperado_rfc:
            error(
                "CFDI-030",
                "Receptor@Rfc",
                f"el comprobante va a {emitido} y el viaje es del cliente {esperado_rfc}",
            )

    # --- complemento Carta Porte ----------------------------------------
    carta_porte = _buscar(raiz, "CartaPorte")
    if carta_porte is None:
        if exige_carta_porte:
            error("CP-001", "CartaPorte", "el traslado exige complemento Carta Porte y no lo trae")
    else:
        _validar_carta_porte(carta_porte, catalogos, error, aviso)

    if not catalogos.completo:
        aviso(
            "CFDI-000",
            "catalogos",
            f"catalogo {catalogos.version} es un subconjunto: una clave valida fuera de el se "
            f"reporta como error sin serlo. No sustituye la validacion XSD del SAT",
        )

    return DictamenCFDI(
        dictamen=Dictamen(ambito="cfdi", hallazgos=hallazgos),
        catalogo_version=catalogos.version,
        catalogo_completo=catalogos.completo,
        cfdi_version=version,
        con_carta_porte=carta_porte is not None,
    )


def _validar_carta_porte(nodo: ET.Element, catalogos: CatalogosSAT, error, aviso) -> None:
    """Las reglas del complemento que rechazan más seguido: mercancía, ubicaciones y distancia."""
    versiones = [str(v) for v in (catalogos.carta_porte.get("versiones_aceptadas") or [])]
    version = nodo.get("Version", "")
    if version and versiones and version not in versiones:
        error("CP-002", "CartaPorte@Version", f"version {version} fuera de las aceptadas: {', '.join(versiones)}")

    ubicaciones = _hijo(nodo, "Ubicaciones")
    tipos = [u.get("TipoUbicacion") for u in _hijos(ubicaciones, "Ubicacion")]
    if "Origen" not in tipos:
        error("CP-003", "Ubicaciones", "falta la ubicacion de Origen")
    if "Destino" not in tipos:
        error("CP-003", "Ubicaciones", "falta la ubicacion de Destino")

    mercancias = _hijo(nodo, "Mercancias")
    if mercancias is None or not _hijos(mercancias, "Mercancia"):
        # La regla que más rechaza en la práctica: un traslado sin mercancía declarada.
        error("CP-004", "Mercancias", "el complemento no declara ninguna Mercancia")

    distancia = _decimal(mercancias.get("TotalDistRec")) if mercancias is not None else None
    if distancia is None:
        error("CP-005", "Mercancias@TotalDistRec", "falta la distancia total recorrida")
    elif distancia <= 0:
        error("CP-005", "Mercancias@TotalDistRec", f"la distancia recorrida es {distancia}")

    autotransporte = _buscar(nodo, "Autotransporte")
    if autotransporte is None:
        error("CP-006", "Autotransporte", "el complemento no trae Autotransporte")
    else:
        if not autotransporte.get("PermSCT") or not autotransporte.get("NumPermisoSCT"):
            error("CP-006", "Autotransporte@PermSCT", "falta el permiso SCT o su numero")
        vehiculo = _hijo(autotransporte, "IdentificacionVehicular")
        if vehiculo is None:
            error("CP-007", "IdentificacionVehicular", "falta la identificacion vehicular")
        else:
            config = vehiculo.get("ConfigVehicular")
            permitidas = catalogos.claves("config_autotransporte", "carta_porte")
            if config and permitidas and config not in permitidas:
                error("CP-007", "IdentificacionVehicular@ConfigVehicular", f"{config!r} fuera de catalogo")

    contenedor = _buscar(nodo, "FiguraTransporte")
    figura = _buscar(contenedor, "TiposFigura") if contenedor is not None else None
    if figura is None:
        error("CP-008", "FiguraTransporte", "el complemento no declara la figura de transporte")
        return
    permitidos = catalogos.claves("tipos_figura", "carta_porte")
    tipo = figura.get("TipoFigura")
    if tipo and permitidos and tipo not in permitidos:
        error("CP-008", "TiposFigura@TipoFigura", f"{tipo!r} fuera de catalogo")
    if not (figura.get("NumLicencia") or "").strip():
        # Advertencia y no error: el operador puede no ser quien conduce en todo el trayecto.
        aviso("CP-009", "TiposFigura@NumLicencia", "la figura de transporte no trae numero de licencia")
