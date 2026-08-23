/**
 * Un caso que espera a una persona, con todo lo que hace falta para decidir sobre el.
 *
 * Junta tres fuentes que viven en sitios distintos y no se pueden juntar en SQL:
 *
 *   Postgres  el caso: desde cuando espera, su criticidad, su `ultimo_seq`.
 *   git       el registro: de que equipo es el agente, quien responde, quien mas aprueba.
 *   git       las politicas: el plazo de SLA y el calendario laboral que lo cuenta.
 *
 * Por eso el cruce se hace aqui y no en una consulta. Meter el organigrama en Postgres para
 * poder filtrar con un `where` seria crear la segunda verdad que §7 existe para no tener: el
 * dia que cambie un `owner_humano` en `registry/teams/`, la bandeja seguiria enrutando al
 * anterior hasta que alguien se acordara de sincronizar la tabla.
 */

import type { Caso } from "./db/consultas";
import { puedeAprobar, responsableDe, type Decision, type Persona, type Registro } from "./rbac";
import { calendario, conFestivos, resolverVencimiento, vencimiento } from "./reglas/sla";

export interface HitlPendiente {
  caso: Caso;
  /** El agente cuyo caso es. Sale de `casos.responsable`, que el plegado deja en el actor. */
  agenteId: string;
  /** Quien RESPONDE por el. Uno solo: la responsabilidad compartida entre tres es de nadie. */
  responsable: string | null;
  /** El umbral que disparo el gate, si el evento lo declaro. */
  umbral: string | undefined;
  /** Cuando vence, en ms UTC. Contado en horas habiles, no en horas de reloj. */
  venceEnMs: number;
  /** Negativo si ya vencio. Es lo que ordena la bandeja. */
  restanteMs: number;
  /** Que toca hacer si ya vencio. Nunca es "aprobar". `null` si todavia no vence. */
  alVencer: ReturnType<typeof resolverVencimiento>;
  /** Si ESTA persona puede aprobarlo, y por que si o por que no. */
  decision: Decision;
}

/**
 * La bandeja de una persona, ordenada por lo que menos tiempo le queda.
 *
 * `soloLosSuyos` filtra a lo que le llega; en falso devuelve todo, que es lo que necesita el
 * resumen para decir cuantos HITL hay abiertos en total sin mentir por omision.
 */
export const bandejaDe = (args: {
  casos: Caso[];
  persona: Persona | null;
  registro: Registro;
  umbrales?: Record<string, string>;
  /**
   * Los festivos declarados en Postgres. Sin ellos el reloj cuenta un feriado como dia
   * habil y el SLA vence antes de tiempo — por eso quien llama tiene que traerlos, y tiene
   * que tratar el fallo de lectura como un error, no como una lista vacia.
   */
  festivos?: Iterable<string>;
  ahora?: number;
  soloLosSuyos?: boolean;
}): HitlPendiente[] => {
  const ahora = args.ahora ?? Date.now();
  const umbrales = args.umbrales ?? {};
  // Una sola vez para toda la bandeja: armarlo por caso seria recorrer la lista de festivos
  // tantas veces como casos haya, para obtener siempre lo mismo.
  const cal = args.festivos ? conFestivos(calendario(), args.festivos) : calendario();

  const pendientes = args.casos.map((caso): HitlPendiente => {
    const agenteId = caso.responsable;
    const umbral = umbrales[caso.trace_id];
    // El reloj del SLA arranca cuando el caso entro a esperar, que es su ultima
    // actualizacion: es el mismo criterio que usa `RunLog.vencidos()` en Python.
    const espera = new Date(caso.actualizado_en).getTime();
    const venceEnMs = vencimiento(espera, caso.criticidad, cal);

    return {
      caso,
      agenteId,
      responsable: responsableDe(agenteId, args.registro),
      umbral,
      venceEnMs,
      restanteMs: venceEnMs - ahora,
      alVencer: resolverVencimiento({
        traceId: caso.trace_id,
        criticidad: caso.criticidad,
        esperaDesde: espera,
        ahora,
        escalamientos: caso.escalamientos,
        calendario: cal,
      }),
      decision: args.persona
        ? puedeAprobar({ persona: args.persona, agenteId, umbral, registro: args.registro })
        : {
            puede: false,
            motivo:
              "No se sabe quien eres: tu cuenta de Clerk no esta vinculada a una persona del registro.",
          },
    };
  });

  const visibles =
    args.soloLosSuyos && args.persona
      ? pendientes.filter((p) => leVisible(p, args.persona as Persona, args.registro))
      : pendientes;

  // Lo mas cerca de vencer primero, y lo ya vencido antes que todo — sale solo, porque el
  // restante de un caso vencido es negativo. Ordenar por fecha de creacion, que es lo que
  // hace una bandeja normal, enterraria justo lo que urge.
  return visibles.sort((a, b) => a.restanteMs - b.restanteMs);
};

/**
 * Si este HITL aparece en la bandeja de esta persona.
 *
 * Ver NO es aprobar. Un co-owner ve el caso de su equipo aunque el gate no lo faculte para el
 * umbral: se entera y puede empujar a quien si. Esconderselo convertiria un SLA a punto de
 * vencer en una sorpresa.
 */
const leVisible = (p: HitlPendiente, persona: Persona, registro: Registro): boolean => {
  if (p.decision.puede) return true;
  if (persona.nombre === p.responsable) return true;
  const agente = registro.agentes[p.agenteId];
  if (!agente) return false;
  return agente.equipos.some(
    (e) => persona.equiposResponsable.includes(e) || persona.equiposApoyo.includes(e),
  );
};

/** El restante, en palabras. Negativo se dice como vencido, no como "-3 h". */
export const restanteLegible = (ms: number): string => {
  const vencido = ms < 0;
  const abs = Math.abs(ms);
  const min = Math.round(abs / 60_000);
  const cuerpo =
    min < 60 ? `${min} min` : min < 1440 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${Math.floor(min / 1440)} d`;
  return vencido ? `vencido hace ${cuerpo}` : `${cuerpo}`;
};
