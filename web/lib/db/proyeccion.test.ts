/**
 * La proyeccion `casos` tiene que poder reconstruirse plegando `eventos`.
 *
 * §6 lo dice como garantia, no como aspiracion: *"se reconstruye plegando `eventos` … si
 * divergiera, se tira y se vuelve a plegar. Eso es lo que la hace segura."* Una proyeccion
 * que NO se puede reconstruir sin cambiar deja de ser una proyeccion y pasa a ser una segunda
 * verdad — exactamente lo que este portal existe para no tener.
 *
 * El riesgo es silencioso: la divergencia no rompe nada visible. La pantalla sigue pintando
 * lo que dice `casos`, y sólo el dia que alguien repliegue el registro —para auditar, para
 * migrar, para responder «¿quien decidio esto en marzo?»— aparecen dos respuestas distintas.
 *
 * Estas pruebas repliegan en SQL con las mismas reglas de `RunLog.casos()` y exigen que
 * coincida con la proyeccion, fila por fila y campo por campo. Se saltan solas sin base.
 */

import { existsSync, readFileSync } from "node:fs";

import { beforeAll, describe, expect, it } from "vitest";

const cargarEntorno = (): boolean => {
  if (process.env.DATABASE_URL) return true;
  if (!existsSync(".env.local")) return false;
  const env = readFileSync(".env.local", "utf-8");
  const url = (env.match(/^DATABASE_URL\s*=\s*"?([^"\n]+)"?/m) || [])[1]?.trim();
  if (!url || url.includes("CONTRASENA") || url.includes("PON_AQUI")) return false;
  process.env.DATABASE_URL = url;
  return true;
};

const hayCredenciales = cargarEntorno();

/**
 * El plegado, en SQL, con las reglas de `services/runlog/registro.py:casos()`:
 *
 *   pasos          los eventos `paso`
 *   estado         el destino de la ultima transicion, o `recibido` si no hubo ninguna
 *   responsable    el actor del ultimo evento — una transicion deja como responsable a quien la hizo
 *   reintentos     las transiciones rechazado_validacion -> en_proceso
 *   escalamientos  las transiciones cuyo motivo empieza con "escalamiento"
 *   ultimo_seq     el mayor seq del trace
 */
const PLEGADO = `
  with plegado as (
    select trace_id,
           count(*) filter (where evento = 'paso')                                       as pasos,
           max(seq)                                                                      as ultimo_seq,
           (array_agg(datos->>'a' order by seq desc)
              filter (where evento = 'transicion'))[1]                                   as estado,
           (array_agg(actor order by seq desc))[1]                                        as responsable,
           count(*) filter (where evento = 'transicion'
                            and datos->>'de' = 'rechazado_validacion'
                            and datos->>'a'  = 'en_proceso')                             as reintentos,
           count(*) filter (where evento = 'transicion'
                            and datos->>'motivo' like 'escalamiento%')                   as escalamientos
      from eventos group by trace_id
  )
  select c.trace_id,
         c.estado, coalesce(p.estado, 'recibido')  as f_estado,
         c.responsable, p.responsable              as f_responsable,
         c.pasos, p.pasos                          as f_pasos,
         c.ultimo_seq, p.ultimo_seq                as f_ultimo_seq,
         c.reintentos, p.reintentos                as f_reintentos,
         c.escalamientos, p.escalamientos          as f_escalamientos
    from casos c join plegado p using (trace_id)
`;

describe.skipIf(!hayCredenciales)("la proyeccion se puede replegar", () => {
  let consultar: (sql: string) => Promise<Record<string, unknown>[]>;

  beforeAll(async () => {
    const { filas } = await import("./cliente");
    consultar = async (sql) => {
      const r = await filas<Record<string, unknown>>(sql);
      if (!r.ok) throw new Error(r.detalle);
      return r.datos;
    };
  });

  it("todo caso proyectado tiene sus eventos, y al reves", async () => {
    // Un caso sin apertura rompe el plegado entero: `RunLog.casos()` levanta
    // ErrorDeIntegridad en cuanto ve un evento de un trace que nunca se abrio.
    const huerfanos = await consultar(`
      select 'caso sin eventos' as que, c.trace_id from casos c
        where not exists (select 1 from eventos e where e.trace_id = c.trace_id)
      union all
      select 'eventos sin caso', e.trace_id from eventos e
        where not exists (select 1 from casos c where c.trace_id = e.trace_id)
      union all
      select 'trace sin apertura', e.trace_id from eventos e
        group by e.trace_id
        having count(*) filter (where e.evento = 'apertura') = 0
    `);
    expect(huerfanos).toEqual([]);
  });

  it("el seq de cada caso empieza en 1 y no salta", async () => {
    // El candado de §8.4 se apoya en que `ultimo_seq + 1` este libre. Un hueco en la
    // secuencia significa que alguien escribio fuera de la ruta de escritura.
    const rotos = await consultar(`
      select trace_id from eventos group by trace_id
       having min(seq) <> 1 or max(seq) <> count(*)
    `);
    expect(rotos).toEqual([]);
  });

  it("cada campo de la proyeccion coincide con el plegado", async () => {
    // LA PRUEBA. Si alguien agrega una ruta de escritura que mueve el estado sin mover la
    // proyeccion —o al reves— esto se pone rojo antes de que nadie audite nada.
    const divergen = await consultar(`
      ${PLEGADO}
      where c.estado        is distinct from coalesce(p.estado, 'recibido')
         or c.responsable   is distinct from p.responsable
         or c.pasos         is distinct from p.pasos
         or c.ultimo_seq    is distinct from p.ultimo_seq
         or c.reintentos    is distinct from p.reintentos
         or c.escalamientos is distinct from p.escalamientos
    `);
    expect(divergen).toEqual([]);
  });

  it("ningun motivo humano puede confundirse con un escalamiento", async () => {
    // El plegado cuenta un escalamiento cuando el motivo EMPIEZA con "escalamiento". Los
    // motivos que escribe una persona van prefijados con su decision, asi que no pueden
    // colisionar. Si alguna vez uno lo hiciera, el conteo de escalamientos derivaria.
    const sospechosos = await consultar(`
      select trace_id, seq, datos->>'motivo' as motivo
        from eventos
       where evento = 'transicion'
         and datos->>'motivo' like 'escalamiento%'
         and autor_persona is not null
    `);
    expect(sospechosos).toEqual([]);
  });

  it("todo evento con autor apunta a una persona que existe", async () => {
    // `autor_persona` es una FK, asi que Postgres ya lo impone. Se comprueba igual porque
    // un uuid colgando se veria en pantalla como «—», indistinguible de un evento de agente.
    const colgando = await consultar(`
      select e.trace_id, e.seq from eventos e
       where e.autor_persona is not null
         and not exists (select 1 from personas p where p.id = e.autor_persona)
    `);
    expect(colgando).toEqual([]);
  });

  it("ningun caso quedo en un estado que la maquina no permite", async () => {
    const invalidos = await consultar(`
      select trace_id, estado from casos
       where estado not in ('recibido','en_proceso','esperando_validacion',
                            'rechazado_validacion','esperando_humano','entregado',
                            'bloqueado','expirado')
    `);
    expect(invalidos).toEqual([]);
  });

  it("ningun caso paso de los dos reintentos que permite caso.py", async () => {
    // MAX_REINTENTOS = 2. Al tercer rechazo el caso se bloquea. Es aritmetica, no criterio.
    const pasados = await consultar(`select trace_id, reintentos from casos where reintentos > 2`);
    expect(pasados).toEqual([]);
  });
});

describe.skipIf(hayCredenciales)("sin credenciales", () => {
  it("no se comprobo que la proyeccion se pueda replegar, y queda dicho", () => {
    expect(hayCredenciales).toBe(false);
  });
});
