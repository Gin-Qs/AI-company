"""Los festivos, leidos de Postgres (scripts/sql/0003).

Por que no viven en el YAML como el resto del calendario: el huso, la jornada y los dias
habiles son **mecanismo** —cambian casi nunca y un umbral que se edita desde una pantalla es
un umbral sin auditoria—. Los festivos son un **catalogo de la empresa** que cambia cada ano
y que nadie va a mantener por pull request. La prueba esta a la vista: la lista lleva vacia
desde que existe el calendario.

Lo que no se pierde al moverlos es la auditoria, que era la razon de tenerlos en git: cada
fila dice quien la declaro, cuando y de donde salio. Es mas de lo que daba el YAML, donde
`git blame` decia quien edito el archivo pero no de donde vino el dato.

Si la base no responde se levanta `BaseIlegible`. Una lista de festivos vacia no es un error
visible: es un calendario que afirma que se trabaja todos los dias, y el SLA vence antes.
"""

from __future__ import annotations

from datetime import date

from services.common.postgres import BaseIlegible, consultar, dsn

SQL = "select fecha, motivo, origen, alcance from festivos order by fecha"


def leer(cadena: str | None = None) -> list[dict]:
    """Los festivos declarados, con su procedencia."""
    filas = consultar(SQL, cadena=cadena, que="la lista de festivos")
    return [{"fecha": f[0], "motivo": f[1], "origen": f[2], "alcance": f[3]} for f in filas]


def fechas(cadena: str | None = None) -> frozenset[date]:
    """Solo las fechas, que es lo que el calendario necesita para contar."""
    return frozenset(f["fecha"] for f in leer(cadena))


__all__ = ["BaseIlegible", "dsn", "fechas", "leer"]
