/**
 * La conexion a Postgres, y —mas importante— que hace el portal cuando no la hay.
 *
 * Hoy no la hay. `DATABASE_URL` sigue con el marcador de la contrasena, porque Supabase la
 * genero al crear el proyecto por API y nadie la vio nunca (docs/portal.md §15). Eso no es
 * un detalle de configuracion: decide como se ven tres vistas del portal.
 *
 * LA DECISION. Una vista sin base de datos puede hacer dos cosas, y solo una es aceptable:
 *
 *   (a) pintar ceros, tablas vacias y barras al 0%. Se ve como un sistema que funciona y no
 *       tiene nada que reportar. Es indistinguible de la verdad, y es mentira.
 *   (b) decir en pantalla que no hay conexion, por que, y que falta para que la haya.
 *
 * Se hace (b), siempre. Por eso ninguna consulta de este modulo devuelve `T`: devuelven
 * `Lectura<T>`, que obliga a quien pinta la pagina a decidir que ensena cuando no hay datos.
 * Un tipo que no se puede ignorar es la unica forma de que esto siga siendo verdad dentro de
 * seis meses.
 */

import { Pool } from "pg";

/** El resultado de mirar la base: o hay datos, o hay una razon que se puede leer en pantalla. */
export type Lectura<T> =
  | { ok: true; datos: T }
  | { ok: false; motivo: Motivo; detalle: string };

export type Motivo = "sin_configurar" | "marcador" | "error";

export const sinDatos = <T,>(motivo: Motivo, detalle: string): Lectura<T> => ({
  ok: false,
  motivo,
  detalle,
});

/**
 * Por que no hay base, si es que no la hay. `null` significa que la cadena existe y parece
 * una cadena de verdad — no que la conexion funcione, eso solo lo dice intentarlo.
 */
export const porQueNoHayBase = (): { motivo: Motivo; detalle: string } | null => {
  const url = process.env.DATABASE_URL?.trim();

  if (!url) {
    return {
      motivo: "sin_configurar",
      detalle:
        "DATABASE_URL no esta definida. En local se lee de web/.env.local; en Vercel, de las " +
        "variables de entorno del proyecto.",
    };
  }

  // El marcador merece su propio mensaje. Es el estado real de hoy, y confundirlo con "no
  // configurada" manda a buscar la contrasena a quien tiene que RESTABLECERLA: Supabase la
  // genero al crear el proyecto por API y no la muestra despues.
  if (url.includes("CONTRASENA") || url.includes("PON_AQUI")) {
    return {
      motivo: "marcador",
      detalle:
        "DATABASE_URL trae el marcador de la contrasena, no la contrasena. Supabase la genero " +
        "al crear el proyecto por API y no vuelve a mostrarla: hay que restablecerla en " +
        "Project Settings -> Database -> Reset database password, y pegarla en web/.env.local.",
    };
  }

  return null;
};

export const hayBase = (): boolean => porQueNoHayBase() === null;

/**
 * Una sola pool por proceso, guardada en `globalThis`.
 *
 * Vercel corre funciones serverless: cada invocacion podria abrir su propia conexion y dejar
 * a Postgres sin cupo. Por eso `DATABASE_URL` apunta al pooler (puerto 6543) y la pool de aqui
 * se queda corta a proposito. El cache en `globalThis` ademas sobrevive al recarga en caliente
 * de `next dev`, que si no abre una pool nueva en cada guardado hasta agotar el cupo.
 */
const cache = globalThis as unknown as { __poolPortal?: Pool };

const pool = (): Pool => {
  if (!cache.__poolPortal) {
    cache.__poolPortal = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 3,
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 8_000,
    });
  }
  return cache.__poolPortal;
};

/**
 * Corre una consulta y nunca lanza: devuelve `Lectura`.
 *
 * Que no lance es a proposito. Una excepcion en un Server Component tumba la pagina entera y
 * el portal desaparece justo cuando lo que hacia falta era que dijera que le pasa. Un error
 * de base de datos es informacion, no un accidente que haya que esconder.
 *
 * `filas` SIEMPRE se llama con parametros: `%1, $2...`. Ninguna cadena se concatena al SQL.
 */
export const filas = async <T,>(sql: string, parametros: unknown[] = []): Promise<Lectura<T[]>> => {
  const falta = porQueNoHayBase();
  if (falta) return sinDatos<T[]>(falta.motivo, falta.detalle);

  try {
    const resultado = await pool().query(sql, parametros);
    return { ok: true, datos: resultado.rows as T[] };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : String(error);
    return sinDatos<T[]>(
      "error",
      // El mensaje crudo de Postgres se enseña a proposito: quien entra al portal es
      // Direccion o quien opera, no un anonimo, y "algo salio mal" no ha reparado nunca nada.
      `La consulta a Postgres fallo: ${mensaje}`,
    );
  }
};

/** La primera fila, o `null` si no hubo ninguna. Misma disciplina: no lanza. */
export const fila = async <T,>(sql: string, parametros: unknown[] = []): Promise<Lectura<T | null>> => {
  const resultado = await filas<T>(sql, parametros);
  if (!resultado.ok) return resultado;
  return { ok: true, datos: resultado.datos[0] ?? null };
};

/**
 * Una transaccion. Todo lo que escribe el portal pasa por aqui.
 *
 * `BEGIN` / `COMMIT` sobre UNA conexion tomada de la pool, no sobre la pool: `pool.query()`
 * puede darle cada sentencia a una conexion distinta, y entonces el `BEGIN` y el `INSERT`
 * viven en transacciones diferentes. El sintoma seria un caso aprobado sin su evento, o al
 * reves, y solo bajo concurrencia — la clase de error que no aparece hasta que hay dos
 * personas usando el portal.
 *
 * A diferencia de `filas`, esto SI propaga la excepcion. Quien escribe necesita distinguir
 * una violacion de `unique (trace_id, seq)` —que significa "alguien te gano", §8.4— de
 * cualquier otro fallo, y para eso hace falta el error de Postgres con su codigo.
 */
export const enTransaccion = async <T,>(
  trabajo: (ejecutar: (sql: string, parametros?: unknown[]) => Promise<{ rows: unknown[] }>) => Promise<T>,
): Promise<T> => {
  const falta = porQueNoHayBase();
  if (falta) throw new Error(falta.detalle);

  const conexion = await pool().connect();
  try {
    await conexion.query("begin");
    const resultado = await trabajo((sql, parametros) => conexion.query(sql, parametros));
    await conexion.query("commit");
    return resultado;
  } catch (error) {
    await conexion.query("rollback").catch(() => {
      // Si el rollback tambien falla, la conexion esta perdida; `release` la descarta.
      // Tragarse este error es correcto: el que importa es el de arriba.
    });
    throw error;
  } finally {
    conexion.release();
  }
};

/** El codigo de Postgres para "violaste una restriccion unica". Es el candado de §8.4. */
export const CHOQUE_DE_SEQ = "23505";

export const esChoqueDeSeq = (error: unknown): boolean =>
  typeof error === "object" && error !== null && (error as { code?: string }).code === CHOQUE_DE_SEQ;
