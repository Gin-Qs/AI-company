/**
 * Las consultas del portal, contra Postgres de verdad.
 *
 * Es la unica prueba del repositorio que necesita la base, y existe porque hay una clase de
 * error que ninguna otra atrapa: **el SQL no se tipa**. `tsc` valida que `Caso.costo_mxn` sea
 * `string` y no mira si la columna se llama asi; una tabla que cambia de forma compila
 * perfecto y falla en la primera peticion. Estas pruebas son el unico sitio donde el esquema
 * real y el codigo se miran a la cara.
 *
 * SE SALTA SOLA si no hay base, y lo dice. No falla: quien clona el repositorio y corre las
 * pruebas no tiene por que tener credenciales de Postgres, y la CI tampoco. Pero una prueba
 * saltada no es una prueba en verde, y vitest lo reporta como omitida — la misma distincion
 * que la vista 7 hace con las reglas del registro.
 *
 * Las cifras NO se fijan en duro contra el contenido de la base. Se afirman relaciones e
 * invariantes: que el `seq` no salte, que el dinero llegue como cadena, que el join a
 * `personas` resuelva. Sembrar un encargo nuevo no puede poner esto rojo.
 */

import { existsSync, readFileSync } from "node:fs";

import { beforeAll, describe, expect, it } from "vitest";

// El entorno se carga ANTES de importar nada de `lib/db`: el cliente lee `process.env` al
// construir la pool, y una importacion estatica arriba se adelantaria a esto.
const RUTA_ENV = ".env.local";

const cargarEntorno = (): boolean => {
  if (process.env.DATABASE_URL) return true;
  if (!existsSync(RUTA_ENV)) return false;
  const env = readFileSync(RUTA_ENV, "utf-8");
  const leer = (n: string) =>
    (env.match(new RegExp(`^${n}\\s*=\\s*"?([^"\\n]+)"?`, "m")) || [])[1]?.trim();
  const url = leer("DATABASE_URL");
  if (!url || url.includes("CONTRASENA") || url.includes("PON_AQUI")) return false;
  process.env.DATABASE_URL = url;
  return true;
};

const hayCredenciales = cargarEntorno();

describe.skipIf(!hayCredenciales)("las consultas contra el esquema real", () => {
  let q: typeof import("./consultas");

  beforeAll(async () => {
    q = await import("./consultas");
  });

  it("los casos se leen y el buscador filtra por sus cuatro campos", async () => {
    const todos = await q.buscarCasos();
    expect(todos.ok).toBe(true);
    if (!todos.ok) return;
    expect(todos.datos.length).toBeGreaterThan(0);

    // Se busca con un valor tomado de la propia base, no con una constante: asi la prueba
    // sigue valiendo cuando cambie lo que hay sembrado.
    const uno = todos.datos[0]!;
    for (const termino of [uno.trace_id, uno.referencia, uno.responsable, uno.tipo]) {
      if (!termino) continue;
      const filtrado = await q.buscarCasos(termino);
      expect(filtrado.ok, termino).toBe(true);
      if (filtrado.ok) expect(filtrado.datos.length, termino).toBeGreaterThan(0);
    }
  });

  it("la historia de un caso viene en orden de seq, sin huecos", async () => {
    const todos = await q.buscarCasos();
    if (!todos.ok || todos.datos.length === 0) return;

    const historia = await q.historiaDe(todos.datos[0]!.trace_id);
    expect(historia.ok).toBe(true);
    if (!historia.ok) return;
    const seqs = historia.datos.map((e) => e.seq);
    expect(seqs).toEqual([...Array(seqs.length).keys()].map((i) => i + 1));
  });

  it("`ultimo_seq` coincide con el ultimo evento de cada caso", async () => {
    // Es el candado de §8.4. Si el proyectado y el registro se separan, la primera
    // aprobacion falla o —peor— dos personas escriben el mismo seq.
    const todos = await q.buscarCasos();
    if (!todos.ok) return;
    for (const caso of todos.datos) {
      const historia = await q.historiaDe(caso.trace_id);
      if (!historia.ok) continue;
      const ultimo = historia.datos.at(-1)?.seq ?? 0;
      expect(caso.ultimo_seq, caso.trace_id).toBe(ultimo);
    }
  });

  it("el join a personas resuelve el autor cuando lo hay", async () => {
    // `autor_persona` es una FK. Que el nombre salga prueba que la siembra no dejo uuids
    // colgando: un autor que no resuelve se ve igual que un evento sin autor.
    const todos = await q.buscarCasos();
    if (!todos.ok) return;
    let vistos = 0;
    for (const caso of todos.datos.slice(0, 5)) {
      const historia = await q.historiaDe(caso.trace_id);
      if (!historia.ok) continue;
      for (const e of historia.datos) {
        if (e.autor_nombre !== null) {
          expect(typeof e.autor_nombre).toBe("string");
          expect(e.autor_nombre.length).toBeGreaterThan(0);
          vistos += 1;
        }
      }
    }
    expect(vistos).toBeGreaterThan(0);
  });

  it("ningun importe llega como number", async () => {
    // §8.3. `pg` devuelve `numeric` como cadena; si alguien le pusiera un parser a ese tipo,
    // el consumo derivaria por centavos y el corte duro del 100% se dispararia tarde.
    const todos = await q.buscarCasos();
    if (!todos.ok) return;
    for (const c of todos.datos) {
      expect(typeof c.costo_mxn, c.trace_id).toBe("string");
      expect(typeof c.tokens, c.trace_id).toBe("string");
    }
  });

  it("las agregaciones corren: estados, HITL, umbrales y consumo", async () => {
    // Cuatro consultas con casts y `jsonb ->>` que solo fallan contra el esquema real.
    const periodo = new Date().toISOString().slice(0, 7);
    for (const [nombre, lectura] of [
      ["casosPorEstado", await q.casosPorEstado()],
      ["hitlAbiertos", await q.hitlAbiertos()],
      ["umbralesPorCaso", await q.umbralesPorCaso()],
      ["consumoDelPeriodo", await q.consumoDelPeriodo(periodo)],
      ["consumoDelPeriodo (sembrado)", await q.consumoDelPeriodo("2026-08")],
    ] as const) {
      expect(lectura.ok, nombre).toBe(true);
    }
  });

  it("la salud del registro se consulta aunque la CI no haya publicado nada", async () => {
    // El caso normal hoy: la consulta corre y devuelve null. Que devuelva null NO es lo
    // mismo que que falle, y la vista 7 los pinta distinto.
    const r = await q.ultimaValidacion("main");
    expect(r.ok).toBe(true);
  });

  it("toda persona vinculada a Clerk resuelve a una autoridad del registro", async () => {
    // La cadena de §7: clerk_user_id -> personas.nombre -> authority-gate.yaml -> rol.
    // Se rompe en silencio si alguien vincula una cuenta de Clerk a un nombre que el gate no
    // conoce: la sesion entra, el rol sale `sin_rol`, y la persona ve un portal vacio sin que
    // nada diga por que. Aqui se entera.
    const { cargarRegistro, resolverPersona } = await import("../rbac");
    const registro = cargarRegistro();
    const vinculadas = await q.personasVinculadas();
    expect(vinculadas.ok).toBe(true);
    if (!vinculadas.ok) return;

    for (const fila of vinculadas.datos) {
      const persona = resolverPersona(fila.nombre, registro);
      expect(persona.rol, `${fila.nombre} no aparece en authority-gate.yaml`).not.toBe("sin_rol");
    }
  });

  it("el historial de pausas trae quien la puso y quien la levanto", async () => {
    const r = await q.historialDePausas();
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    for (const p of r.datos) {
      expect(p.motivo.length).toBeGreaterThan(0);
      expect(p.se_reanuda_cuando.length).toBeGreaterThan(0);
      // Una pausa cerrada tiene las tres cosas del levantamiento, o ninguna. A medias
      // significaria que se levanto sin decir por que.
      if (p.hasta !== null) expect(p.reanudada_porque).not.toBeNull();
    }
  });
});

describe.skipIf(hayCredenciales)("sin credenciales de Postgres", () => {
  it("se salta el contrato contra el esquema real, y queda dicho", () => {
    // Este `it` existe para que la corrida diga en voz alta que NO se comprobo el SQL. Una
    // suite que simplemente no incluye un archivo se ve igual que una que lo paso.
    expect(hayCredenciales).toBe(false);
  });
});
