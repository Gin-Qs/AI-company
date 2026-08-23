"""La pausa de la oficina, leida de Postgres (docs/portal.md §4).

POR QUE ESTE MODULO EXISTE. El portal escribe la pausa en Postgres, y `runtime.convocar()`
la lee en cada convocatoria. Si cada uno mirara un sitio distinto, **la pausa no pausaria**:
Direccion detendria la oficina desde la pantalla y el CLI seguiria convocando agentes tan
tranquilo. Dos verdades sobre el control de maximo privilegio del sistema es exactamente el
error que el portal existe para evitar, asi que la fuente se mueve aqui y `office/pausa.yaml`
queda como historico congelado.

TRES SITUACIONES, y la tercera es la que importa:

    sin base configurada   se lee el YAML. Es el modo de desarrollo local de siempre.
    base configurada, OK   manda Postgres.
    base configurada, cae  **se levanta una excepcion**. NO se asume "oficina abierta".

La tercera es una decision, no un descuido. Un control que ante la duda deja pasar no es un
control: si la base no responde, nadie puede afirmar que la oficina no este pausada, y
convocar a un agente sobre esa suposicion es justo lo que la pausa impide. Que el CLI truene
con un mensaje claro es preferible a que trabaje durante una pausa que no pudo leer.
"""

from __future__ import annotations

from services.common.postgres import MARCADORES, dsn  # noqa: F401 - se reexportan


class PausaIlegible(RuntimeError):
    """Hay base de datos configurada y no se pudo preguntar si la oficina esta en pausa."""


SQL = """
    select p.desde, p.motivo, p.se_reanuda_cuando, quien.nombre
      from pausa p
      left join personas quien on quien.id = p.por
     where p.hasta is null
     limit 1
"""


def leer(cadena: str | None = None) -> dict:
    """La pausa activa segun Postgres, con la forma que ya devolvia `leer_pausa()`.

    Devuelve `{"activa": False}` solo cuando la base **respondio** y no hay pausa abierta.
    """
    conexion_str = cadena or dsn()
    if not conexion_str:
        raise PausaIlegible("no hay base de datos configurada")

    try:
        import psycopg  # noqa: PLC0415 - opcional: pip install -e ".[postgres]"
    except ModuleNotFoundError as falta:
        raise PausaIlegible(
            "hay base de datos configurada pero falta psycopg, asi que no se puede comprobar "
            "si la oficina esta en pausa. Instalalo con: pip install -e \".[postgres]\""
        ) from falta

    try:
        with psycopg.connect(conexion_str, connect_timeout=15) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(SQL)
                fila = cursor.fetchone()
    except Exception as error:  # noqa: BLE001 - cualquier fallo de red o de permisos cuenta igual
        raise PausaIlegible(
            f"no se pudo leer la pausa de Postgres ({type(error).__name__}: {error}). "
            f"No se convoca a nadie sin poder comprobar que la oficina esta abierta."
        ) from error

    if fila is None:
        return {"activa": False, "fuente": "postgres"}

    desde, motivo, se_reanuda, por = fila
    return {
        "activa": True,
        "fuente": "postgres",
        "desde": desde.isoformat() if hasattr(desde, "isoformat") else str(desde),
        "por": por or "sin declarar",
        "motivo": motivo,
        "se_reanuda_cuando": se_reanuda,
    }
