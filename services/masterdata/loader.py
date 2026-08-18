"""Carga del catalogo desde archivos planos.

La Fase 0 no elige base de datos: el ERP todavia no existe. El catalogo vive
en CSV y un YAML de parametros, que es lo que hoy se puede exportar de la
operacion real. Cuando exista `erp/`, cambia este modulo y nada mas: los
servicios de calculo reciben un `Catalogo`, no un archivo.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Iterable, Iterator, TypeVar

import yaml

from services.common.errors import ErrorDeIntegridad, ErrorDeValidacion
from services.masterdata.catalogo import Catalogo
from services.masterdata.models import (
    Cliente,
    Operador,
    Parametros,
    Ruta,
    Tarifa,
    Unidad,
)

T = TypeVar("T")

ARCHIVOS = {
    "clientes": "clientes.csv",
    "unidades": "unidades.csv",
    "operadores": "operadores.csv",
    "rutas": "rutas.csv",
    "tarifas": "tarifas.csv",
    "parametros": "parametros.yaml",
}


def leer_csv(ruta: Path) -> Iterator[dict[str, str]]:
    """Lee un CSV con encabezado, tolerando BOM de Excel y espacios en los titulos."""
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            yield {
                (clave or "").strip().lower(): (valor if valor is not None else "")
                for clave, valor in fila.items()
                if clave is not None
            }


def _indexar(
    filas: Iterable[dict[str, str]],
    constructor: Callable[[dict[str, str]], T],
    clave: Callable[[T], str],
    entidad: str,
) -> dict[str, T]:
    indice: dict[str, T] = {}
    for numero, fila in enumerate(filas, start=2):  # 1 es el encabezado
        try:
            registro = constructor(fila)
        except ErrorDeValidacion as exc:
            raise ErrorDeValidacion(
                f"{entidad}: fila {numero}: {exc.mensaje}", campo=exc.campo, fila=numero, entidad=entidad
            ) from exc
        identificador = clave(registro)
        if identificador in indice:
            raise ErrorDeIntegridad(
                f"{entidad}: identificador duplicado {identificador!r} (fila {numero})",
                campo=entidad,
                fila=numero,
            )
        indice[identificador] = registro
    return indice


def cargar_catalogo(directorio: str | Path, *, estricto: bool = True) -> Catalogo:
    """Construye el catalogo desde `directorio`.

    Con `estricto=True` (el default) un problema de integridad detiene la
    carga. La Fase 0 se apoya en esto: mas vale no producir costo por km que
    producirlo sobre un catalogo roto.
    """
    base = Path(directorio)
    if not base.is_dir():
        raise ErrorDeValidacion(f"no existe el directorio de catalogo: {base}", campo="directorio")

    faltantes = [nombre for nombre in ARCHIVOS.values() if not (base / nombre).is_file()]
    if faltantes:
        raise ErrorDeValidacion(
            f"faltan archivos del catalogo en {base}: {', '.join(sorted(faltantes))}", campo="directorio"
        )

    catalogo = Catalogo(
        clientes=_indexar(leer_csv(base / ARCHIVOS["clientes"]), Cliente.desde_fila, lambda c: c.cliente_id, "clientes"),
        unidades=_indexar(leer_csv(base / ARCHIVOS["unidades"]), Unidad.desde_fila, lambda u: u.unit_id, "unidades"),
        operadores=_indexar(
            leer_csv(base / ARCHIVOS["operadores"]), Operador.desde_fila, lambda o: o.operador_id, "operadores"
        ),
        rutas=_indexar(leer_csv(base / ARCHIVOS["rutas"]), Ruta.desde_fila, lambda r: r.route_id, "rutas"),
        tarifas=list(
            _indexar(leer_csv(base / ARCHIVOS["tarifas"]), Tarifa.desde_fila, lambda t: t.tarifa_id, "tarifas").values()
        ),
        parametros=cargar_parametros(base / ARCHIVOS["parametros"]),
    )

    if estricto:
        catalogo.exigir_integridad()
    return catalogo


def cargar_parametros(ruta: str | Path) -> Parametros:
    contenido = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    if not isinstance(contenido, dict):
        raise ErrorDeValidacion("parametros.yaml debe ser un mapa", campo="parametros")
    catalogo_version = contenido.get("version")
    datos = dict(contenido)
    if catalogo_version is not None:
        datos["version"] = str(catalogo_version)
    return Parametros.desde_dict(datos)
