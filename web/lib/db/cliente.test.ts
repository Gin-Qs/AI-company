/**
 * Lo que el portal hace cuando NO hay base de datos.
 *
 * Es la parte que mas facil se rompe sin que nadie lo note, porque romperla se ve bien: una
 * vista que pinta ceros en vez de decir que no se conecto parece un sistema sano. Estas
 * pruebas fijan el comportamiento contrario y lo dejan fijado.
 *
 * Ninguna abre una conexion. No hace falta: lo que se comprueba es la decision de antes de
 * conectarse, que es donde vive el riesgo.
 */

import { afterEach, describe, expect, it } from "vitest";

import { filas, hayBase, porQueNoHayBase, sinDatos } from "./cliente";

const original = process.env.DATABASE_URL;

afterEach(() => {
  if (original === undefined) delete process.env.DATABASE_URL;
  else process.env.DATABASE_URL = original;
});

describe("por que no hay base", () => {
  it("dice `sin_configurar` cuando la variable no existe", () => {
    delete process.env.DATABASE_URL;
    expect(porQueNoHayBase()?.motivo).toBe("sin_configurar");
  });

  it("dice `sin_configurar` cuando la variable esta vacia o en blanco", () => {
    process.env.DATABASE_URL = "   ";
    expect(porQueNoHayBase()?.motivo).toBe("sin_configurar");
  });

  it("distingue el marcador de la contrasena de una variable sin poner", () => {
    // Es el estado real de hoy (web/.env.local). Confundirlo con "sin configurar" manda a
    // BUSCAR una contrasena que hay que RESTABLECER: Supabase la genero por API y no la
    // vuelve a mostrar. El mensaje tiene que llevar a la accion correcta.
    process.env.DATABASE_URL =
      "postgresql://postgres.abc:CONTRASENA@aws-0-us-east-1.pooler.supabase.com:6543/postgres";
    const falta = porQueNoHayBase();
    expect(falta?.motivo).toBe("marcador");
    expect(falta?.detalle).toMatch(/restablecerla/i);
  });

  it("tambien reconoce el otro marcador que usa web/.env.local", () => {
    process.env.DATABASE_URL = "postgresql://postgres:PON_AQUI_TU_CONTRASENA@localhost:5432/x";
    expect(porQueNoHayBase()?.motivo).toBe("marcador");
  });

  it("no se queja de una cadena que parece de verdad", () => {
    process.env.DATABASE_URL = "postgresql://postgres:hunter2@localhost:5432/postgres";
    expect(porQueNoHayBase()).toBeNull();
    expect(hayBase()).toBe(true);
  });
});

describe("una consulta sin base", () => {
  it("no lanza: devuelve la razon, para que la pagina la pueda pintar", async () => {
    // Una excepcion en un Server Component tumba la pagina entera, y el portal desaparece
    // justo cuando lo que hacia falta era que dijera que le pasa.
    delete process.env.DATABASE_URL;
    const resultado = await filas("select 1");
    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.motivo).toBe("sin_configurar");
      expect(resultado.detalle.length).toBeGreaterThan(0);
    }
  });

  it("nunca devuelve un arreglo vacio disfrazado de exito", async () => {
    // Este es EL error que estas pruebas existen para impedir. Un `{ ok: true, datos: [] }`
    // sin base se pinta como "no hay casos" y se lee como "todo tranquilo".
    process.env.DATABASE_URL = "postgresql://u:CONTRASENA@h:6543/d";
    const resultado = await filas("select 1");
    expect(resultado).not.toMatchObject({ ok: true });
  });
});

describe("la forma del resultado", () => {
  it("obliga a mirar `ok` antes de leer los datos", () => {
    // El tipo es una union discriminada: sin comprobar `ok`, `datos` no existe. Es a
    // proposito, y esta prueba lo deja escrito por si alguien lo ablanda a `T | null`.
    const malo = sinDatos<number[]>("error", "se cayo");
    expect(malo.ok).toBe(false);
    expect(Object.keys(malo)).not.toContain("datos");
  });
});
