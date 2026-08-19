"""Linea de comandos de la capa deterministica.

    python -m services.cli fase0 --datos data/ejemplo            # costo por km y margen real
    python -m services.cli cotizar --ruta R-MTY-CDMX --unidad U-101 --cliente CL-01
    python -m services.cli facturar --viaje T-1001 --cliente CL-01 --flete 26500 \
        --documentos orden_de_servicio,carta_porte,pod           # Fase 2
    python -m services.cli cartera --datos data/ejemplo --corte 2026-06-30

Sin agentes y sin ACT-*: aqui solo corre codigo. `fase0` es el default si no se nombra
subcomando, para no romper la invocacion documentada de la Fase 0.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from services.ar import cartera_desde_operacion
from services.common.errors import ErrorDeServicio
from services.doc_checklist import Documento, revisar as revisar_expediente
from services.invoicing import EntradaFactura, armar_borrador, conceptos_de_viaje
from services.masterdata import cargar_catalogo, fecha as parse_fecha
from services.pipeline import ReporteFase0, ejecutar_fase0
from services.pricing import Autorizacion, EntradaCotizacion, cotizar, dictaminar
from services.trace import Libro

ANCHO = 78


def _linea(titulo: str = "") -> str:
    if not titulo:
        return "-" * ANCHO
    return f"-- {titulo} " + "-" * max(ANCHO - len(titulo) - 4, 0)


def render(reporte: ReporteFase0) -> str:
    partes: list[str] = []
    resumen = reporte.catalogo.resumen()
    partes.append(_linea("CATALOGO (svc-masterdata)"))
    partes.append(
        "  " + "  ".join(f"{entidad}: {total}" for entidad, total in resumen.items())
    )

    partes.append(_linea("INGESTA (svc-ingest)"))
    for nombre, resultado in reporte.ingestas.items():
        datos = resultado.resumen()
        partes.append(
            f"  {nombre:<8} aceptados {datos['aceptados']:>5}   rechazados {datos['rechazados']:>4}"
            f"   duplicados {datos['duplicados']:>4}   tasa rechazo {datos['tasa_rechazo_pct']}%"
        )
        for rechazo in resultado.rechazos[:3]:
            partes.append(f"           fila {rechazo.fila}: [{rechazo.codigo}] {rechazo.motivo}")
        if len(resultado.rechazos) > 3:
            partes.append(f"           ... y {len(resultado.rechazos) - 3} rechazo(s) mas")

    if reporte.precios_diesel:
        partes.append(_linea("PRECIO DE DIESEL PONDERADO POR LITROS"))
        for periodo, precio in sorted(reporte.precios_diesel.items()):
            partes.append(f"  {periodo}   $ {precio}/litro")

    partes.append(_linea("COSTO Y MARGEN (svc-costing + svc-profitability)"))
    if not reporte.margenes:
        partes.append("  Sin viajes costeados.")
    else:
        d = reporte.distribucion
        partes.append(
            f"  viajes {d.viajes}   ingreso $ {d.ingreso_mxn}   costo $ {d.costo_mxn}   margen $ {d.margen_mxn}"
        )
        partes.append(
            f"  margen ponderado {d.ponderado_pct}%   mediana {d.mediana_pct}%   "
            f"p25 {d.p25_pct}%   p75 {d.p75_pct}%   en perdida: {d.viajes_en_perdida}"
        )
        partes.append("")
        partes.append("  Peor margen por dimension (los primeros son los que hay que mirar):")
        for dimension, agregados in reporte.agregados.items():
            partes.append(f"    {dimension}:")
            for a in agregados[:5]:
                partes.append(
                    f"      {a.clave:<12} viajes {a.viajes:>3}  margen {a.margen_pct:>7}%  "
                    f"costo/km $ {a.costo_por_km:>8}  perdida {a.viajes_en_perdida}"
                )

    if reporte.contraste:
        partes.append(_linea("CONTRASTE CONTRA LA TABLA DE PRECIOS"))
        c = reporte.contraste.resumen()
        partes.append(
            f"  evaluados {c['evaluados']}   por debajo del minimo {c['desviaciones']}   "
            f"sin tarifa vigente {c['sin_tarifa_vigente']}   sin margen declarado {c['sin_margen_declarado']}"
        )
        for desviacion in reporte.contraste.desviaciones[:5]:
            partes.append(
                f"    {desviacion.trip_id:<10} {desviacion.route_id:<8} real {desviacion.margen_real_pct}%  "
                f"minimo {desviacion.margen_minimo_pct}%  brecha {desviacion.brecha_pp} pp"
            )

    if reporte.no_costeados:
        partes.append(_linea("VIAJES NO COSTEADOS"))
        for viaje in reporte.no_costeados[:10]:
            partes.append(f"  {viaje.trip_id:<10} [{viaje.codigo}] {viaje.motivo}")
        if len(reporte.no_costeados) > 10:
            partes.append(f"  ... y {len(reporte.no_costeados) - 10} mas")

    partes.append(_linea())
    return "\n".join(partes)


def render_cotizacion(cotizacion, dictamen) -> str:
    """La cotizacion como la leeria una persona: primero quien autoriza, luego los numeros."""
    partes = [_linea("COTIZACION (svc-pricing)")]
    partes.append(f"  {cotizacion.cliente_id}  {cotizacion.route_id}  unidad {cotizacion.unit_id}  {cotizacion.fecha}")
    partes.append("")
    partes.append(f"  precio          $ {cotizacion.precio_mxn:>12}   tabla {cotizacion.tarifa_id}: $ {cotizacion.precio_tabla_mxn}")
    partes.append(f"  costo total     $ {cotizacion.costo_mxn:>12}   costo/km $ {cotizacion.costo_por_km}")
    partes.append(f"  margen          $ {cotizacion.margen_mxn:>12}   {cotizacion.margen_pct}%  (minimo de la ruta {cotizacion.margen_minimo_pct}%)")
    if cotizacion.descuento_pct > 0:
        partes.append(f"  descuento         {cotizacion.descuento_pct}%")
    partes.append("")
    partes.append(f"  AUTORIZA: {cotizacion.nivel_autorizacion.upper()} ({cotizacion.quien_autoriza})")
    partes.append(f"  motivo:   {cotizacion.motivo_gate}")
    if cotizacion.autorizacion:
        partes.append(f"  excepcion autorizada por {cotizacion.autorizacion.quien}: {cotizacion.autorizacion.motivo}")

    if cotizacion.assumptions:
        partes.append(_linea("SUPUESTOS"))
        for supuesto in cotizacion.assumptions:
            partes.append(f"  {supuesto.campo:<22} {supuesto.valor:>12}   {supuesto.detalle}")

    partes.append(_linea("CIFRAS PARA svc-trace"))
    for nombre, valor in cotizacion.cifras.items():
        partes.append(f"  {nombre:<22} {valor:>12}   {cotizacion.fuentes[nombre]}")

    partes.append(_linea("DICTAMEN (svc-validation)"))
    if dictamen.ok:
        partes.append("  sin hallazgos")
    for hallazgo in dictamen.hallazgos:
        partes.append(f"  [{hallazgo.severidad}] {hallazgo}")
    partes.append(_linea())
    return "\n".join(partes)


def render_expediente(expediente) -> str:
    partes = [_linea("EXPEDIENTE (svc-doc-checklist)")]
    estado = "COMPLETO" if expediente.completo else "INCOMPLETO"
    partes.append(
        f"  viaje {expediente.trip_id}   servicio {expediente.tipo_de_servicio}   {estado}"
        + ("" if expediente.catalogo_confirmado else "   (catalogo sin confirmar)")
    )
    for presente in expediente.presentes:
        partes.append(f"    ok      {presente.tipo}")
    for faltante in expediente.faltantes + expediente.vencidos:
        marca = "FALTA " if faltante.motivo == "falta" else "VENCE "
        obligatorio = "obligatorio" if faltante.obligatorio else "opcional"
        partes.append(f"    {marca}  {faltante.tipo:<24} {obligatorio}")
    for ajeno in expediente.no_corresponden:
        partes.append(f"    AJENO   {ajeno.tipo} (viaje {ajeno.trip_id or 'sin viaje'})")
    return "\n".join(partes)


def render_borrador(borrador) -> str:
    partes = [_linea("BORRADOR (svc-invoicing)")]
    partes.append(f"  {borrador.identificador}   viaje {borrador.trip_id}   receptor {borrador.receptor_rfc}")
    for concepto in borrador.conceptos:
        partes.append(
            f"    {concepto.tipo:<10} {concepto.cantidad:>6} x {concepto.valor_unitario_mxn:>12}"
            f" = {concepto.importe_mxn:>12}   {concepto.clave_prod_serv}/{concepto.clave_unidad}"
        )
    partes.append(f"  {'subtotal':<14} $ {borrador.subtotal_mxn:>14}")
    partes.append(f"  {'IVA':<14} $ {borrador.iva_mxn:>14}")
    partes.append(f"  {'retencion':<14} $ {borrador.retencion_mxn:>14}")
    partes.append(f"  {'TOTAL':<14} $ {borrador.total_mxn:>14}")
    partes.append("")
    partes.append("  TIMBRADO: no lo hace el sistema. ACT-DOC-S es CTL-HITL siempre (11.4).")
    if borrador.assumptions:
        partes.append(_linea("SUPUESTOS"))
        for supuesto in borrador.assumptions:
            partes.append(f"  {supuesto.campo:<22} {supuesto.valor:>10}   {supuesto.detalle}")
    return "\n".join(partes)


def render_cartera(resultado) -> str:
    cartera = resultado.cartera
    partes = [_linea("CARTERA (svc-ar)")]
    partes.append(
        f"  corte {cartera.corte}   {len(resultado.facturas)} facturas   {len(resultado.pagos)} abonos"
        f"   rubrica {cartera.rubrica_version}" + ("" if cartera.rubrica_calibrada else " (sin calibrar)")
    )
    partes.append("")
    for tramo, monto in cartera.aging.items():
        partes.append(f"    {tramo:<12} $ {monto:>14}")
    partes.append(f"    {'TOTAL':<12} $ {cartera.saldo_total_mxn:>14}   vencido $ {cartera.saldo_vencido_mxn}")
    if cartera.dias_cartera is not None:
        partes.append(f"    dias cartera (DSO): {cartera.dias_cartera}")
    if cartera.sin_identificar_mxn > 0:
        partes.append(f"    sin identificar:    $ {cartera.sin_identificar_mxn}  (no se reparte; hay que conciliar)")

    if cartera.prioridad:
        partes.append(_linea("PRIORIDAD DE COBRANZA"))
        for fila in cartera.prioridad[:10]:
            partes.append(
                f"  {fila['factura_id']:<12} {fila['cliente_id']:<7} $ {fila['saldo_mxn']:>12}"
                f"   {fila['dias_vencido']:>4} dias   {fila['tramo']:<9} {fila['accion']}"
            )
    if cartera.flujo_esperado:
        partes.append(_linea("FLUJO ESPERADO (lo que aun no vence)"))
        for semana, monto in cartera.flujo_esperado.items():
            partes.append(f"  {semana}   $ {monto:>14}")
    partes.append(_linea("SUPUESTOS"))
    for supuesto in resultado.supuestos:
        partes.append(f"  - {supuesto}")
    partes.append(_linea())
    return "\n".join(partes)


def _comando_facturar(args) -> int:
    """Expediente y borrador. Nunca timbra: eso lo autoriza una persona en la bandeja."""
    try:
        catalogo = cargar_catalogo(Path(args.datos) / "catalogo")
        fecha = parse_fecha(args.fecha) if args.fecha else date.today()
        documentos = [
            Documento(tipo=tipo.strip(), trip_id=args.viaje)
            for tipo in (args.documentos or "").split(",")
            if tipo.strip()
        ]
        expediente = revisar_expediente(
            trip_id=args.viaje,
            tipo_de_servicio=args.tipo_servicio,
            documentos=documentos,
            fecha_corte=fecha,
        )
        print(render_expediente(expediente))

        borrador = armar_borrador(
            EntradaFactura(
                trip_id=args.viaje,
                cliente_id=args.cliente,
                conceptos=conceptos_de_viaje(
                    precio_flete_mxn=Decimal(args.flete),
                    demoras_horas=Decimal(args.demoras) if args.demoras else None,
                    tarifa_demora_mxn_hora=Decimal(args.tarifa_demora) if args.tarifa_demora else None,
                    estadias_dias=Decimal(args.estadias) if args.estadias else None,
                    tarifa_estadia_mxn_dia=Decimal(args.tarifa_estadia) if args.tarifa_estadia else None,
                ),
                fecha=fecha,
                serie=args.serie,
                trace_id=args.trace or "",
            ),
            catalogo,
            expediente,
        )
    except ErrorDeServicio as exc:
        # Que no se pueda facturar no es un fallo del programa: es la puerta funcionando.
        print(f"NO SE FACTURA\n  {exc}", file=sys.stderr)
        return 3

    print(render_borrador(borrador))
    print(_linea())
    return 1      # siempre queda esperando una firma humana


def _comando_cartera(args) -> int:
    try:
        resultado = cartera_desde_operacion(
            args.datos, corte=parse_fecha(args.corte) if args.corte else date.today()
        )
    except ErrorDeServicio as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2

    print(render_cartera(resultado))
    if args.salida_json:
        destino = Path(args.salida_json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(resultado.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Reporte JSON escrito en {destino}")
    return 0


def _comando_fase0(args) -> int:
    try:
        reporte = ejecutar_fase0(args.datos)
    except ErrorDeServicio as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2

    print(render(reporte))

    if args.salida_json:
        destino = Path(args.salida_json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(reporte.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Reporte JSON escrito en {destino}")

    # Un viaje sin costear no es un detalle: es un hueco en la cifra que se va a usar.
    return 1 if reporte.no_costeados or any(not i.ok for i in reporte.ingestas.values()) else 0


def _comando_cotizar(args) -> int:
    try:
        catalogo = cargar_catalogo(Path(args.datos) / "catalogo")
        autorizacion = (
            Autorizacion(quien=args.autoriza, motivo=args.motivo or "autorizacion manual")
            if args.autoriza
            else None
        )
        libro = Libro(trace_id=args.trace or "TR-CLI")
        cotizacion = cotizar(
            EntradaCotizacion(
                route_id=args.ruta,
                unit_id=args.unidad,
                cliente_id=args.cliente,
                operador_id=args.operador,
                fecha=parse_fecha(args.fecha) if args.fecha else date.today(),
                fuel_price=Decimal(args.diesel) if args.diesel else None,
                descuento_pct=Decimal(args.descuento) if args.descuento else None,
                precio_propuesto_mxn=Decimal(args.precio) if args.precio else None,
            ),
            catalogo,
            autorizacion=autorizacion,
            libro=libro,
        )
    except ErrorDeServicio as exc:
        # El bloqueo del gate no es un fallo del programa: es el programa haciendo su trabajo.
        print(f"NO SE GENERA LA COTIZACION\n  {exc}", file=sys.stderr)
        return 3

    print(render_cotizacion(cotizacion, dictaminar(cotizacion)))
    return 0 if not cotizacion.requiere_humano else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capa deterministica: Fase 0 y Fase 1.")
    sub = parser.add_subparsers(dest="comando")

    fase0 = sub.add_parser("fase0", help="costo por km y margen real (Fase 0)")
    fase0.add_argument("--datos", default="data/ejemplo", help="directorio con catalogo/ y operacion/")
    fase0.add_argument("--json", dest="salida_json", help="escribe el reporte completo en este archivo")

    cot = sub.add_parser("cotizar", help="cotiza una ruta contra la tabla pre-aprobada (Fase 1)")
    cot.add_argument("--datos", default="data/ejemplo")
    cot.add_argument("--ruta", required=True)
    cot.add_argument("--unidad", required=True)
    cot.add_argument("--cliente", required=True)
    cot.add_argument("--operador")
    cot.add_argument("--fecha", help="AAAA-MM-DD; por omision, hoy")
    cot.add_argument("--diesel", help="precio por litro; por omision, el de referencia del catalogo")
    cot.add_argument("--descuento", help="porcentaje de descuento sobre la tarifa de tabla")
    cot.add_argument("--precio", help="precio propuesto en pesos, alternativa a --descuento")
    cot.add_argument("--autoriza", help="quien autoriza una excepcion bajo el margen minimo")
    cot.add_argument("--motivo", help="motivo de la excepcion")
    cot.add_argument("--trace", help="trace_id del caso, para ligar las cifras")

    fac = sub.add_parser("facturar", help="expediente y borrador de comprobante (Fase 2)")
    fac.add_argument("--datos", default="data/ejemplo")
    fac.add_argument("--viaje", required=True)
    fac.add_argument("--cliente", required=True)
    fac.add_argument("--flete", required=True, help="precio del flete en pesos")
    fac.add_argument("--documentos", default="", help="tipos separados por coma; ver requisitos-documentales.yaml")
    fac.add_argument("--tipo-servicio", dest="tipo_servicio", default="carga_general")
    fac.add_argument("--fecha", help="AAAA-MM-DD; por omision, hoy")
    fac.add_argument("--serie", help="serie del comprobante; por omision, la de la politica")
    fac.add_argument("--demoras", help="horas de demora")
    fac.add_argument("--tarifa-demora", dest="tarifa_demora", help="pesos por hora de demora")
    fac.add_argument("--estadias", help="dias de estadia")
    fac.add_argument("--tarifa-estadia", dest="tarifa_estadia", help="pesos por dia de estadia")
    fac.add_argument("--trace", help="trace_id del caso")

    car = sub.add_parser("cartera", help="aging, prioridad de cobranza y flujo esperado (Fase 2)")
    car.add_argument("--datos", default="data/ejemplo")
    car.add_argument("--corte", help="AAAA-MM-DD; por omision, hoy")
    car.add_argument("--json", dest="salida_json", help="escribe la cartera completa en este archivo")

    # Compatibilidad: `--datos ...` sin subcomando sigue siendo la Fase 0.
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if not argumentos or argumentos[0].startswith("-"):
        argumentos = ["fase0", *argumentos]

    args = parser.parse_args(argumentos)
    comandos = {
        "cotizar": _comando_cotizar,
        "facturar": _comando_facturar,
        "cartera": _comando_cartera,
    }
    return comandos.get(args.comando, _comando_fase0)(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
