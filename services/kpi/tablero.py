"""svc-kpi — indicadores homologados con semáforo, sin calcular ninguno (§6.6, R2).

R2 del §9: **un número, una fuente.** El margen sigue siendo de `svc-profitability`, el DSO de
`svc-ar`, los días de caja de `svc-treasury`. Este servicio no recalcula ninguno: toma el valor
que ya produjo el servicio de origen, lo homologa contra el catálogo de KPIs, le pone semáforo
contra la meta declarada y lo agrupa por departamento.

Un valor que llega sin entrada en el catálogo no se reporta como KPI — se rechaza, porque un
indicador sin fuente declarada es exactamente el tipo de número que nadie puede auditar.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from services.common.errors import ErrorDeServicio, ErrorDeValidacion
from services.common.money import cantidad

RAIZ = Path(__file__).resolve().parent.parent.parent
CATALOGO_POR_DEFECTO = RAIZ / "registry" / "policies" / "kpis.yaml"

DIRECCIONES = ("mayor_mejor", "menor_mejor")


class KPIDesconocido(ErrorDeServicio):
    """Se pidió reportar un KPI que no está en el catálogo. No hay indicador improvisado."""

    codigo = "KPI-DESCONOCIDO"


@dataclass(frozen=True)
class DefinicionKPI:
    kpi_id: str
    nombre: str
    departamento: str
    fuente: str
    unidad: str
    direccion: str
    meta: Decimal | None


@dataclass(frozen=True)
class CatalogoKPI:
    version: str
    aprobado: bool
    tolerancia_amarilla_pct: Decimal
    kpis: dict[str, DefinicionKPI]

    def definicion(self, kpi_id: str) -> DefinicionKPI:
        if kpi_id not in self.kpis:
            raise KPIDesconocido(
                f"no existe el KPI {kpi_id!r} en el catalogo; declarados: {', '.join(sorted(self.kpis))}",
                campo="kpi_id",
            )
        return self.kpis[kpi_id]


def cargar_catalogo(ruta: str | Path | None = None) -> CatalogoKPI:
    destino = Path(ruta) if ruta else CATALOGO_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}

    kpis: dict[str, DefinicionKPI] = {}
    for identificador, crudo in (datos.get("kpis") or {}).items():
        direccion = str((crudo or {}).get("direccion") or "")
        if direccion not in DIRECCIONES:
            raise ErrorDeValidacion(
                f"el KPI {identificador} declara direccion {direccion!r}; debe ser una de {DIRECCIONES}",
                campo="direccion",
            )
        meta_cruda = (crudo or {}).get("meta")
        kpis[str(identificador)] = DefinicionKPI(
            kpi_id=str(identificador),
            nombre=str((crudo or {}).get("nombre") or identificador),
            departamento=str((crudo or {}).get("departamento") or ""),
            fuente=str((crudo or {}).get("fuente") or ""),
            unidad=str((crudo or {}).get("unidad") or ""),
            direccion=direccion,
            meta=cantidad(meta_cruda) if meta_cruda is not None else None,
        )

    return CatalogoKPI(
        version=str(datos.get("version") or "v0"),
        aprobado=bool(datos.get("aprobado")),
        tolerancia_amarilla_pct=cantidad(datos.get("tolerancia_amarilla_pct", 10)),
        kpis=kpis,
    )


@dataclass(frozen=True)
class Indicador:
    kpi_id: str
    nombre: str
    departamento: str
    fuente: str
    unidad: str
    valor: Decimal
    meta: Decimal | None
    estado: str   # verde | amarillo | rojo | sin_meta

    def as_dict(self) -> dict[str, object]:
        return {
            "kpi_id": self.kpi_id,
            "nombre": self.nombre,
            "departamento": self.departamento,
            "fuente": self.fuente,
            "unidad": self.unidad,
            "valor": str(self.valor),
            "meta": str(self.meta) if self.meta is not None else None,
            "estado": self.estado,
        }


@dataclass(frozen=True)
class Tablero:
    periodo: str
    catalogo_version: str
    indicadores: list[Indicador]

    def por_departamento(self) -> dict[str, list[Indicador]]:
        agrupado: dict[str, list[Indicador]] = {}
        for indicador in self.indicadores:
            agrupado.setdefault(indicador.departamento, []).append(indicador)
        return dict(sorted(agrupado.items()))

    def as_dict(self) -> dict[str, object]:
        return {
            "periodo": self.periodo,
            "catalogo_version": self.catalogo_version,
            "indicadores": [i.as_dict() for i in self.indicadores],
        }


def _semaforo(valor: Decimal, definicion: DefinicionKPI, tolerancia_pct: Decimal) -> str:
    if definicion.meta is None:
        return "sin_meta"
    meta = definicion.meta
    if definicion.direccion == "mayor_mejor":
        if valor >= meta:
            return "verde"
        limite_amarillo = meta * (1 - tolerancia_pct / 100)
        return "amarillo" if valor >= limite_amarillo else "rojo"

    # menor_mejor
    if valor <= meta:
        return "verde"
    limite_amarillo = meta * (1 + tolerancia_pct / 100)
    return "amarillo" if valor <= limite_amarillo else "rojo"


def construir_tablero(
    valores: dict[str, object], *, periodo: str, catalogo: CatalogoKPI | None = None
) -> Tablero:
    """Empaqueta valores ya calculados. Un KPI sin catálogo levanta, no se ignora en silencio."""
    catalogo = catalogo or cargar_catalogo()
    indicadores = []
    for kpi_id, valor_crudo in valores.items():
        definicion = catalogo.definicion(kpi_id)
        valor = cantidad(valor_crudo, campo=kpi_id)
        estado = _semaforo(valor, definicion, catalogo.tolerancia_amarilla_pct)
        indicadores.append(
            Indicador(
                kpi_id=kpi_id,
                nombre=definicion.nombre,
                departamento=definicion.departamento,
                fuente=definicion.fuente,
                unidad=definicion.unidad,
                valor=valor,
                meta=definicion.meta,
                estado=estado,
            )
        )
    indicadores.sort(key=lambda i: (i.departamento, i.kpi_id))
    return Tablero(periodo=periodo, catalogo_version=catalogo.version, indicadores=indicadores)
