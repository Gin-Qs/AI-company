"""Como se llega a Postgres, y que hacer cuando no se llega.

Vive en `services/common/` y no en `office/` por la direccion de las dependencias: `office/`
importa de `services/`, nunca al reves. `services/runlog/sla.py` necesita los festivos, asi
que lo compartido baja aqui y los dos lados lo consumen sin ciclos.

LA REGLA QUE ORDENA TODO ESTE MODULO. Cuando hay base configurada y no responde, **se
levanta una excepcion**. Nunca se devuelve el valor vacio, y no por prolijidad:

    una pausa que no se pudo leer, devuelta como "no hay pausa", deja convocar durante una pausa
    una lista de festivos vacia es un calendario que dice que se trabaja todos los dias

Los dos fallos son silenciosos y los dos acortan o saltan un control. Un sistema que ante la
duda deja pasar no esta comprobando nada.
"""

from __future__ import annotations

import os

# Lo que trae `.env.example` en lugar de una contrasena. Una cadena con un marcador NO es una
# cadena configurada: tratarla como valida haria que el CLI fallara con un error de
# autenticacion en vez de decir que falta configurar la base.
MARCADORES = ("CONTRASENA", "PON_AQUI")

# `DIRECT_URL` primero: el pooler (6543) lleva `?pgbouncer=true`, un parametro de Prisma que
# libpq rechaza. Para leer estado da igual cual se use, pero la preferencia se declara.
VARIABLES = ("DIRECT_URL", "DATABASE_URL")


class BaseIlegible(RuntimeError):
    """Hay base de datos configurada y no se pudo leer lo que se le pregunto."""


def dsn() -> str | None:
    """La cadena de conexion, o `None` si no hay base configurada de verdad."""
    for variable in VARIABLES:
        valor = (os.environ.get(variable) or "").strip()
        if valor and not any(m in valor for m in MARCADORES):
            return valor
    return None


def consultar(sql: str, *, cadena: str | None = None, que: str = "la consulta") -> list[tuple]:
    """Corre una lectura y devuelve las filas. Lanza `BaseIlegible` ante cualquier fallo.

    `que` describe lo que se estaba leyendo, para que el mensaje diga que se perdio y no solo
    que algo se cayo.
    """
    conexion_str = cadena or dsn()
    if not conexion_str:
        raise BaseIlegible(f"no hay base de datos configurada, asi que no se puede leer {que}")

    try:
        import psycopg  # noqa: PLC0415 - opcional: pip install -e ".[postgres]"
    except ModuleNotFoundError as falta:
        raise BaseIlegible(
            f"hay base de datos configurada pero falta psycopg, asi que no se puede leer {que}. "
            f"Instalalo con: pip install -e \".[postgres]\""
        ) from falta

    try:
        with psycopg.connect(conexion_str, connect_timeout=15) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(sql)
                return list(cursor.fetchall())
    except Exception as error:  # noqa: BLE001 - cualquier fallo de red o permisos cuenta igual
        raise BaseIlegible(
            f"no se pudo leer {que} de Postgres ({type(error).__name__}: {error})"
        ) from error
