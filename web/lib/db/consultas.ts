/**
 * Lo que el portal le pregunta a Postgres. Solo lecturas: las escrituras viven en los route
 * handlers de `app/api/`, donde se valida el rol antes de tocar la base (§12).
 *
 * Dos reglas que se notan en cada tipo de aqui:
 *
 *   * **Ningun importe es `number`.** `numeric` en Postgres, `string` en la frontera (§8.3).
 *     `pg` ya devuelve `numeric` como cadena; los tipos lo declaran para que nadie lo
 *     convierta a float sin darse cuenta. `0.1 + 0.2 !== 0.3` no es una curiosidad cuando lo
 *     que se suma es el consumo de un presupuesto con corte duro al 100%.
 *   * **`ultimo_seq` viaja con el caso.** Es el candado optimista de §8.4: quien aprueba lee
 *     el caso con `ultimo_seq = N` e inserta su evento con `seq = N+1`. Si dos personas
 *     aprueban a la vez, la segunda viola `unique (trace_id, seq)` y su transaccion se
 *     revierte entera. No hay candado que liberar ni estado que comparar.
 */

import { fila, filas, type Lectura } from "./cliente";

// --- casos (vista 6) --------------------------------------------------------

export interface Caso {
  trace_id: string;
  tipo: string;
  referencia: string;
  criticidad: "alta" | "media" | "baja";
  estado: string;
  responsable: string;
  abierto_en: Date;
  actualizado_en: Date;
  reintentos: number;
  escalamientos: number;
  pasos: number;
  tokens: string;
  costo_mxn: string;
  ultimo_seq: number;
}

/**
 * Los casos, del mas movido al mas quieto.
 *
 * `busqueda` filtra por trace, referencia o actor. Va como parametro, no concatenada: el
 * buscador de un portal interno es entrada de usuario igual que cualquier otra.
 */
export const buscarCasos = async (
  busqueda = "",
  limite = 100,
): Promise<Lectura<Caso[]>> => {
  const texto = busqueda.trim();
  if (!texto) {
    return filas<Caso>(
      `select * from casos order by actualizado_en desc limit $1`,
      [limite],
    );
  }
  return filas<Caso>(
    `select * from casos
      where trace_id ilike $1 or referencia ilike $1 or responsable ilike $1 or tipo ilike $1
      order by actualizado_en desc
      limit $2`,
    [`%${texto}%`, limite],
  );
};

export const unCaso = (traceId: string): Promise<Lectura<Caso | null>> =>
  fila<Caso>(`select * from casos where trace_id = $1`, [traceId]);

export interface Evento {
  seq: number;
  evento: "apertura" | "paso" | "transicion";
  ts: Date;
  actor: string;
  autor_nombre: string | null;
  datos: Record<string, unknown>;
}

/**
 * La historia completa de un caso, en orden. `seq` y no `ts`: dos eventos pueden compartir
 * el segundo, y entonces ordenar por fecha reordena la historia. El `seq` es el orden real.
 */
export const historiaDe = (traceId: string): Promise<Lectura<Evento[]>> =>
  filas<Evento>(
    `select e.seq, e.evento, e.ts, e.actor, p.nombre as autor_nombre, e.datos
       from eventos e
       left join personas p on p.id = e.autor_persona
      where e.trace_id = $1
      order by e.seq`,
    [traceId],
  );

export interface ConteoPorEstado {
  estado: string;
  cuantos: string;
}

export const casosPorEstado = (): Promise<Lectura<ConteoPorEstado[]>> =>
  filas<ConteoPorEstado>(
    `select estado, count(*)::text as cuantos from casos group by estado order by estado`,
  );

// --- salud del registro (vista 7) -------------------------------------------

export interface ReglaValidada {
  numero: string;
  descripcion: string;
  /** OK · FALLA · OMITIDA — los cuatro estados de §2.1, con `pendientes` como el cuarto. */
  estado: string;
  fallas: string[];
  pendientes: string[];
  omitida: string;
}

export interface Validacion {
  commit_sha: string;
  rama: string;
  corrido_en: Date;
  reglas: ReglaValidada[];
  en_verde: number;
  en_falla: number;
  omitidas: number;
  pendientes: number;
  pytest_ok: boolean;
  pytest_total: number | null;
}

/**
 * La ultima corrida de la CI para una rama.
 *
 * El portal NO reimplementa las 16 reglas: las lee de aqui (§11). El costo aceptado es que
 * la vista muestra el estado del ultimo commit validado, no del instante — y por eso la
 * consulta trae `commit_sha` y `corrido_en`, que la vista enseña. Una vista que oculta de
 * cuando son sus datos se lee como si fueran de ahora.
 */
export const ultimaValidacion = (rama = "main"): Promise<Lectura<Validacion | null>> =>
  fila<Validacion>(
    `select * from validacion_registro where rama = $1 order by corrido_en desc limit 1`,
    [rama],
  );

/** Cualquier rama, para cuando `main` todavia no tiene ninguna corrida publicada. */
export const ultimaValidacionDeCualquierRama = (): Promise<Lectura<Validacion | null>> =>
  fila<Validacion>(`select * from validacion_registro order by corrido_en desc limit 1`);

// --- HITL abiertos (vistas 2 y 4) -------------------------------------------

/**
 * Los casos que esperan a una persona. Es la bandeja, en crudo.
 *
 * `esperando_humano` es el unico estado de `caso.py` que significa "aqui hace falta alguien".
 * No se filtra por equipo en SQL: quien puede ver cada uno se decide en `lib/hitl.ts`
 * cruzando el registro, que vive en git y no en la base. Filtrar aqui obligaria a duplicar
 * el organigrama en Postgres — la segunda verdad que §7 existe para no tener.
 */
export const hitlAbiertos = (): Promise<Lectura<Caso[]>> =>
  filas<Caso>(
    `select * from casos where estado = 'esperando_humano' order by actualizado_en asc`,
  );

/**
 * El umbral que disparo el gate de un caso, si alguno lo declaro.
 *
 * Vive en `eventos.datos->'gate'->>'umbral'`, no en una columna: el gate es parte del paso
 * que lo disparo. Sin umbral, `puedeAprobar` con politica `co_owners_con_autoridad` niega —
 * y esta bien que niegue: no se aprueba lo que no se sabe que es.
 */
export const umbralesPorCaso = (): Promise<Lectura<{ trace_id: string; umbral: string }[]>> =>
  filas<{ trace_id: string; umbral: string }>(
    `select distinct on (trace_id) trace_id, datos->'gate'->>'umbral' as umbral
       from eventos
      where datos->'gate'->>'umbral' is not null
      order by trace_id, seq desc`,
  );

// --- consumo del periodo (vista 2; la vista 5 completa es Fase C) -----------

export interface Consumo {
  actor: string;
  tokens: string;
  costo_mxn: string;
  pasos: string;
}

/**
 * Tokens y costo por actor en un periodo `AAAA-MM`, agregando `eventos`.
 *
 * NO hay tabla de consumo, y es a proposito (§6): `svc-runlog` provee el consumo y
 * `svc-budget` solo compara. Una tabla acumulada seria la segunda fuente que ese servicio
 * existe para no tener.
 *
 * Se excluyen los `svc-*`: cuestan cero y solo ensucian el panorama (§8.5).
 */
export const consumoDelPeriodo = (periodo: string): Promise<Lectura<Consumo[]>> =>
  filas<Consumo>(
    `select actor,
            sum((datos->>'tokens')::bigint)::text            as tokens,
            sum((datos->>'costo_mxn')::numeric)::text        as costo_mxn,
            count(*)::text                                   as pasos
       from eventos
      where evento = 'paso'
        and actor not like 'svc-%'
        and to_char(ts, 'YYYY-MM') = $1
      group by actor
      having sum((datos->>'tokens')::bigint) > 0
      order by sum((datos->>'costo_mxn')::numeric) desc`,
    [periodo],
  );

// --- pausa de la oficina (vista 9) ------------------------------------------

export interface Pausa {
  id: string;
  desde: Date;
  hasta: Date | null;
  por_nombre: string | null;
  motivo: string;
  se_reanuda_cuando: string;
  reanudada_por_nombre: string | null;
  reanudada_porque: string | null;
}

/**
 * El historial de pausas, la activa primero. El motivo y su levantamiento viven en la MISMA
 * fila —igual que en `office/pausa.yaml`—: si vivieran separados, en un mes nadie sabria si
 * la pausa se levanto porque se cumplio la condicion o porque hacia falta trabajar.
 */
export const historialDePausas = (): Promise<Lectura<Pausa[]>> =>
  filas<Pausa>(
    `select p.id::text as id, p.desde, p.hasta, p.motivo, p.se_reanuda_cuando,
            p.reanudada_porque,
            quien.nombre  as por_nombre,
            levanto.nombre as reanudada_por_nombre
       from pausa p
       left join personas quien   on quien.id   = p.por
       left join personas levanto on levanto.id = p.reanudada_por
      order by p.desde desc`,
  );

// --- quien puede entrar (§7.4) ----------------------------------------------

export interface PersonaVinculada {
  nombre: string;
  clerk_user_id: string;
  activa: boolean;
}

/**
 * Las personas que ya tienen cuenta de Clerk enlazada.
 *
 * No se usa para autorizar nada —eso es `lib/sesion.ts`, una fila a la vez— sino para poder
 * comprobar la invariante que sostiene todo §7: que cada nombre vinculado exista tambien en
 * `authority-gate.yaml`. Un nombre que no este ahi entra al portal y se queda `sin_rol`, que
 * se ve igual que un portal vacio.
 */
export const personasVinculadas = (): Promise<Lectura<PersonaVinculada[]>> =>
  filas<PersonaVinculada>(
    `select nombre, clerk_user_id, activa
       from personas
      where clerk_user_id is not null
      order by nombre`,
  );

/**
 * La pausa activa, con la forma que espera `lib/convocar.ts`.
 *
 * Devuelve `Lectura`, no `Pausa`, y eso es el punto: quien convoca tiene que distinguir
 * «la oficina esta abierta» de «no pude preguntar si esta abierta». Un control que ante la
 * duda deja pasar no es un control, asi que la ruta de convocatoria rechaza las dos veces
 * — pero con mensajes distintos, porque mandan a hacer cosas distintas.
 */
export const pausaActiva = async (): Promise<
  Lectura<{ activa: boolean; desde?: string; por?: string; motivo?: string; seReanudaCuando?: string }>
> => {
  const r = await fila<{
    desde: Date;
    motivo: string;
    se_reanuda_cuando: string;
    por_nombre: string | null;
  }>(
    `select p.desde, p.motivo, p.se_reanuda_cuando, quien.nombre as por_nombre
       from pausa p left join personas quien on quien.id = p.por
      where p.hasta is null
      limit 1`,
  );
  if (!r.ok) return r;
  if (r.datos === null) return { ok: true, datos: { activa: false } };
  return {
    ok: true,
    datos: {
      activa: true,
      desde: new Date(r.datos.desde).toISOString(),
      por: r.datos.por_nombre ?? "sin declarar",
      motivo: r.datos.motivo,
      seReanudaCuando: r.datos.se_reanuda_cuando,
    },
  };
};
