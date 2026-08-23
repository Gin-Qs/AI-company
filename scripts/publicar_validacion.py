"""Escribe el resultado del validador a `validacion_registro` (docs/portal.md §11).

La vista 7 del portal —salud del registro— no reimplementa las 16 reglas: lee la ultima fila
que esta tabla tiene para `main`. Cero duplicacion y cero deriva posible, a cambio de una
cosa que hay que decir en pantalla: la vista muestra el estado **del ultimo commit validado**,
no el del instante. Por eso la fila lleva `commit_sha` y `corrido_en`, y por eso la vista los
enseña en vez de fingir que es en vivo.

Lo corre la CI despues de `validate_registry.py --json`. Fuera de la CI no tiene sentido:
`commit_sha` y `rama` salen del entorno de GitHub Actions, y una fila sin commit haria que el
portal presuma haber validado algo que nadie valido.

    python scripts/publicar_validacion.py validacion.json --pytest-xml pytest.xml

SIN SECRETO NO FALLA, PERO TAMPOCO CALLA. Si `DIRECT_URL` no esta configurado, el script
avisa y sale en 0: el PR de alguien que no tiene acceso a la base no se reprueba por eso. Lo
que no hace es fingir que escribio. Un paso de CI que se salta en silencio es peor que uno
que no existe, porque la vista se queda con datos viejos y nadie sabe desde cuando.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(RAIZ))

SQL = """
    insert into validacion_registro
        (commit_sha, rama, reglas, total_reglas, en_verde, en_falla, omitidas, pendientes,
         pytest_ok, pytest_total)
    values (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
"""


def resumen_de_pytest(xml: Path) -> tuple[bool, int | None]:
    """`(paso, cuantas)` leidos del JUnit XML que escribe `pytest --junitxml`.

    Se lee el archivo en vez de mirar el codigo de salida del paso anterior porque el numero
    hace falta igual, y porque un solo origen para las dos cifras no puede contradecirse:
    "en verde" y "de cuantas" tienen que venir de la misma corrida.

    Si el archivo no existe —la suite ni siquiera arranco— se publica como fallida. Es la
    lectura correcta: nadie demostro que el codigo funcione.
    """
    import xml.etree.ElementTree as ET  # noqa: PLC0415 - solo se usa aqui

    if not xml.is_file():
        return False, None

    raiz = ET.parse(xml).getroot()
    suites = raiz.findall("testsuite") or [raiz]
    total = sum(int(s.get("tests", 0)) for s in suites)
    malas = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    # Cero pruebas no es "todo en verde": es que no se probo nada.
    return (total > 0 and malas == 0), total


def fila(resultado: dict, *, pytest_ok: bool, pytest_total: int | None) -> tuple:
    """La fila que va a la tabla. `validate_registry.py --json` ya emite esta forma."""
    return (
        resultado.get("commit_sha", ""),
        resultado.get("rama", ""),
        json.dumps(resultado.get("reglas", []), ensure_ascii=False),
        # `total_reglas` es `not null` sin default: si no viaja, la insercion revienta. Y
        # tiene que ser el total real, no la suma de las otras cifras — que una regla se
        # quede sin clasificar es informacion, no un error de aritmetica que haya que tapar.
        int(resultado.get("total_reglas", len(resultado.get("reglas", [])))),
        int(resultado.get("en_verde", 0)),
        int(resultado.get("en_falla", 0)),
        int(resultado.get("omitidas", 0)),
        int(resultado.get("pendientes", 0)),
        bool(pytest_ok),
        pytest_total,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publica la salud del registro en Postgres.")
    parser.add_argument("archivo", help="el JSON que escribio validate_registry.py --json")
    parser.add_argument(
        "--pytest-xml",
        metavar="ARCHIVO",
        help="el JUnit XML que escribio pytest --junitxml; de ahi salen pytest_ok y pytest_total",
    )
    args = parser.parse_args(argv)

    resultado = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    pytest_ok, pytest_total = (
        resumen_de_pytest(Path(args.pytest_xml)) if args.pytest_xml else (False, None)
    )
    datos = fila(resultado, pytest_ok=pytest_ok, pytest_total=pytest_total)

    dsn = os.environ.get("DIRECT_URL", "").strip()
    if not dsn or "CONTRASENA" in dsn or "PON_AQUI" in dsn:
        print(
            "::warning title=Salud del registro sin publicar::"
            "DIRECT_URL no esta configurado, asi que esta corrida NO se escribio en "
            "validacion_registro. La vista 7 del portal va a seguir mostrando la ultima "
            "corrida que si se publico, con su fecha. Configura el secreto DIRECT_URL."
        )
        print(f"(lo que se habria escrito: {datos[4]} en verde, {datos[5]} en falla, {datos[6]} omitidas)")
        return 0

    try:
        import psycopg  # noqa: PLC0415
    except ModuleNotFoundError:  # pragma: no cover - depende del entorno
        print("::error::falta psycopg. Instala con: pip install -e \".[postgres]\"")
        return 1

    with psycopg.connect(dsn) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(SQL, datos)
        conexion.commit()

    print(
        f"publicado: {datos[4]} en verde, {datos[5]} en falla, {datos[6]} omitidas "
        f"({datos[0][:8] or 'sin commit'} en {datos[1] or 'sin rama'})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
