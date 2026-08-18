"""Linea de comandos de la Fase 0.

    python -m services.cli --datos data/ejemplo
    python -m services.cli --datos data/ejemplo --json salida.json

Imprime costo por km y margen real. Nada mas. Sin agentes, sin ACT-*.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from services.common.errors import ErrorDeServicio
from services.pipeline import ReporteFase0, ejecutar_fase0

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fase 0 - costo por km y margen real, sin IA.")
    parser.add_argument("--datos", default="data/ejemplo", help="directorio con catalogo/ y operacion/")
    parser.add_argument("--json", dest="salida_json", help="escribe el reporte completo en este archivo")
    args = parser.parse_args(argv)

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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
