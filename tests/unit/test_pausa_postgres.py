"""La pausa como fuente unica (docs/portal.md §4).

El portal escribe la pausa en Postgres y `runtime.convocar()` la lee en cada convocatoria. Si
cada uno mirara un sitio distinto, Direccion pausaria desde la pantalla y el CLI seguiria
convocando: **la pausa no pausaria**. Estas pruebas fijan de donde se lee y, sobre todo, que
pasa cuando no se puede leer.

Ninguna abre una conexion. Lo que se comprueba es la decision de antes de conectarse y el
manejo del fallo, que es donde vive el riesgo.
"""

from __future__ import annotations

import pytest

from office import estado, pausa_pg


@pytest.fixture(autouse=True)
def sin_base(monkeypatch):
    """Cada prueba declara su entorno. Heredar el de la maquina las haria irreproducibles."""
    monkeypatch.delenv("DIRECT_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


# --- de donde se lee ---------------------------------------------------------


def test_sin_base_configurada_se_lee_el_yaml():
    assert pausa_pg.dsn() is None
    pausa = estado.leer_pausa()
    assert "activa" in pausa
    assert pausa.get("fuente") != "postgres"


def test_con_base_configurada_manda_postgres(monkeypatch):
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:secreta@host:5432/db")
    llamado = {}

    def falso_leer(cadena=None):
        llamado["si"] = True
        return {"activa": True, "fuente": "postgres", "motivo": "prueba"}

    monkeypatch.setattr(pausa_pg, "leer", falso_leer)
    pausa = estado.leer_pausa()
    assert llamado.get("si") is True
    assert pausa["fuente"] == "postgres"


def test_direct_url_gana_sobre_database_url(monkeypatch):
    """El pooler no soporta todo; para leer estado da igual, pero la preferencia se declara."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@pooler:6543/db")
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@directo:5432/db")
    assert "directo" in (pausa_pg.dsn() or "")


# --- el marcador no es una contrasena ---------------------------------------


@pytest.mark.parametrize("marcador", ["CONTRASENA", "PON_AQUI_TU_CONTRASENA"])
def test_un_marcador_cuenta_como_sin_configurar(monkeypatch, marcador):
    """Es lo que trae .env.example. Tratarlo como cadena valida haria que el CLI fallara con
    un error de autenticacion en vez de decir que falta configurar la base."""
    monkeypatch.setenv("DIRECT_URL", f"postgresql://postgres:{marcador}@host:5432/db")
    assert pausa_pg.dsn() is None


def test_una_cadena_vacia_cuenta_como_sin_configurar(monkeypatch):
    monkeypatch.setenv("DIRECT_URL", "   ")
    assert pausa_pg.dsn() is None


# --- lo que pasa cuando no se puede leer -------------------------------------


def test_si_la_base_no_responde_NO_se_asume_oficina_abierta(monkeypatch):
    """LA PRUEBA QUE IMPORTA.

    Un control que ante la duda deja pasar no es un control. Si la base no responde, nadie
    puede afirmar que la oficina no este pausada, y convocar sobre esa suposicion es
    exactamente lo que la pausa impide.
    """
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host-que-no-existe:5432/db")

    class PsycopgQueTruena:
        @staticmethod
        def connect(*_args, **_kwargs):
            raise OSError("no se pudo resolver el host")

    monkeypatch.setitem(__import__("sys").modules, "psycopg", PsycopgQueTruena)

    with pytest.raises(pausa_pg.PausaIlegible) as fallo:
        pausa_pg.leer()
    # El mensaje tiene que decir por que no se convoca, no solo que fallo algo.
    assert "no se convoca" in str(fallo.value).lower()


def test_sin_psycopg_tampoco_se_asume_oficina_abierta(monkeypatch):
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setitem(__import__("sys").modules, "psycopg", None)

    with pytest.raises(pausa_pg.PausaIlegible) as fallo:
        pausa_pg.leer()
    assert "psycopg" in str(fallo.value)


def test_leer_sin_base_configurada_es_un_error_no_un_false():
    """`leer()` es para cuando ya se decidio que hay base. Que devolviera `activa: False`
    aqui escondería un error de programacion detras de una respuesta plausible."""
    with pytest.raises(pausa_pg.PausaIlegible):
        pausa_pg.leer()


# --- la forma de la respuesta -----------------------------------------------


def test_una_oficina_abierta_se_declara_con_su_fuente(monkeypatch):
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host:5432/db")

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, *_): pass
        def fetchone(self): return None

    class Conexion:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    class Psycopg:
        @staticmethod
        def connect(*_args, **_kwargs): return Conexion()

    monkeypatch.setitem(__import__("sys").modules, "psycopg", Psycopg)
    assert pausa_pg.leer() == {"activa": False, "fuente": "postgres"}


def test_una_pausa_activa_trae_motivo_y_condicion(monkeypatch):
    """Las dos cosas que el esquema exige `not null`. Una pausa sin condicion de reanudacion
    es una pausa que nadie sabe cuando termina."""
    monkeypatch.setenv("DIRECT_URL", "postgresql://u:p@host:5432/db")

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, *_): pass
        def fetchone(self):
            from datetime import datetime, timezone
            return (datetime(2026, 8, 23, 19, 6, tzinfo=timezone.utc),
                    "Pausa de pruebas", "todos los agentes esten activos", "Gabriel")

    class Conexion:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    class Psycopg:
        @staticmethod
        def connect(*_args, **_kwargs): return Conexion()

    monkeypatch.setitem(__import__("sys").modules, "psycopg", Psycopg)
    pausa = pausa_pg.leer()
    assert pausa["activa"] is True
    assert pausa["por"] == "Gabriel"
    assert pausa["motivo"]
    assert pausa["se_reanuda_cuando"]
    assert pausa["desde"].startswith("2026-08-23")
