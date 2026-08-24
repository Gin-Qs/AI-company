/**
 * La unica ruta de escritura del portal (docs/portal.md §12).
 *
 * Todo `INSERT` pasa por aqui, y aqui se cumplen tres cosas que ningun chequeo del cliente
 * puede garantizar:
 *
 *   1. **El autor es real.** `autor_persona` es una FK a `personas`, poblada desde la sesion
 *      de Clerk. No es el `--autor` de texto libre del CLI —donde cualquiera escribe
 *      `--autor Gabriel`— que es la razon principal por la que el Gate de Autoridad existe
 *      en el papel y no en la operacion.
 *   2. **La maquina de estados se respeta.** Los ocho estados y sus transiciones se copian
 *      literales de `services/runlog/caso.py`. Se validan dos veces: en el `check` de la
 *      columna y aqui, antes de escribir. La segunda da un mensaje que se puede leer; la
 *      primera es la que de verdad impide el dato malo.
 *   3. **Dos personas no se pisan.** Y aqui hay una precision que costo descubrir, porque la
 *      version corta —"lo resuelve `unique (trace_id, seq)`"— es enganosa.
 *
 *      Son DOS defensas, y la que de verdad actua no es la restriccion:
 *
 *      **La primera y la que gana: `select ... for update`.** Quien resuelve toma el lock de
 *      la fila del caso antes de mirar nada. La segunda persona se queda esperando ahi
 *      —comprobado contra Postgres real: 1.5s de espera— y cuando entra ya lee el
 *      `ultimo_seq` NUEVO. Su `ultimoSeqVisto` no cuadra y se va por `TeGanaronDeMano` sin
 *      llegar a insertar.
 *
 *      **La segunda, de red: `unique (trace_id, seq)`.** Solo dispara si algo se salta el
 *      `for update`. Y ojo con como se prueba: una violacion de unicidad **solo se
 *      manifiesta cuando la otra transaccion hace COMMIT**. Dos transacciones que ambas
 *      revierten se dejan escribir la misma `(trace_id, seq)` sin quejarse — la segunda
 *      espera, la primera revierte, y la segunda pasa. Un test que intente provocar la
 *      carrera sin commitear reporta "las dos ganaron" y parece que el candado no existe.
 *
 *      QUIEN QUITE EL `for update` PENSANDO QUE LA RESTRICCION LO CUBRE deja el sistema
 *      dependiendo de la red en vez de la puerta, y con eventos de sobra en el registro.
 *
 * El evento y la proyeccion `casos` se escriben en la MISMA transaccion. Si divergieran, la
 * proyeccion se puede tirar y volver a plegar desde `eventos` — eso es lo que la hace segura,
 * y solo vale si nunca se separan.
 */

import { enTransaccion, esChoqueDeSeq } from "./cliente";

// --- la maquina de estados, copiada literal de services/runlog/caso.py ------

export const TRANSICIONES: Record<string, readonly string[]> = {
  recibido: ["en_proceso", "bloqueado"],
  en_proceso: ["esperando_validacion", "esperando_humano", "bloqueado"],
  esperando_validacion: ["esperando_humano", "rechazado_validacion", "entregado", "bloqueado"],
  rechazado_validacion: ["en_proceso", "bloqueado"],
  esperando_humano: ["entregado", "expirado", "bloqueado"],
  bloqueado: ["en_proceso", "expirado"],
  entregado: [],
  expirado: [],
};

/**
 * Que le pasa a un caso cuando una persona lo resuelve.
 *
 * Aprobar entrega. Rechazar **bloquea**, no expira: expirar es lo que le pasa a un caso que
 * nadie miro, y confundir "lo revise y dije que no" con "se me paso" borraria la diferencia
 * entre una decision y un descuido — justo la distincion que la bandeja existe para crear.
 */
export const DESTINO = { aprobar: "entregado", rechazar: "bloqueado" } as const;
export type Resolucion = keyof typeof DESTINO;

export class TransicionInvalida extends Error {}
export class TeGanaronDeMano extends Error {}

export interface Resuelto {
  traceId: string;
  estado: string;
  seq: number;
}

/**
 * Resuelve un HITL: escribe la transicion y actualiza la proyeccion.
 *
 * `ultimoSeqVisto` es lo que la pantalla tenia cuando la persona hizo clic. No es un detalle
 * de implementacion que se pueda rellenar desde el servidor: es el "yo vi ESTE caso, en ESTE
 * punto de su historia". Recalcularlo aqui convertiria el candado en teatro.
 *
 * La autoridad NO se comprueba en esta funcion. La comprueba quien la llama, con
 * `puedeAprobar()` y la sesion resuelta. Se separa a proposito: mezclar "quien puede" con
 * "como se escribe" es como se termina con dos reglas de autoridad que discrepan.
 */
export const resolverHitl = async (args: {
  traceId: string;
  resolucion: Resolucion;
  personaId: string;
  actor: string;
  motivo: string;
  ultimoSeqVisto: number;
}): Promise<Resuelto> => {
  const destino = DESTINO[args.resolucion];

  try {
    return await enTransaccion(async (ejecutar) => {
      // Se relee el caso DENTRO de la transaccion. El estado que traia la pantalla puede
      // tener minutos; el que decide es el de ahora.
      const actual = await ejecutar(
        `select estado, ultimo_seq, responsable from casos where trace_id = $1 for update`,
        [args.traceId],
      );
      const caso = actual.rows[0] as
        | { estado: string; ultimo_seq: number; responsable: string }
        | undefined;

      if (!caso) throw new TransicionInvalida(`El caso ${args.traceId} no existe.`);

      const permitidos = TRANSICIONES[caso.estado] ?? [];
      if (!permitidos.includes(destino)) {
        throw new TransicionInvalida(
          `${args.traceId} esta en ${caso.estado} y no puede pasar a ${destino}; ` +
            `permitido: ${permitidos.join(", ") || "nada, el caso ya cerro"}.`,
        );
      }

      // El candado. Si alguien escribio entre que se pinto la pantalla y ahora, el seq que
      // la persona vio ya no es el ultimo — y lo que aprobo no es lo que hay.
      if (caso.ultimo_seq !== args.ultimoSeqVisto) {
        throw new TeGanaronDeMano(
          `Este caso cambio mientras lo mirabas: ibas por el evento ${args.ultimoSeqVisto} y ` +
            `ya va en el ${caso.ultimo_seq}. Vuelve a cargarlo antes de decidir.`,
        );
      }

      const seq = caso.ultimo_seq + 1;

      // La insercion que puede chocar. Dos personas con el mismo `seq`: una gana, la otra
      // revierte entera. Nunca dos eventos, nunca una sobrescrita.
      await ejecutar(
        `insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
         values ($1, $2, 'transicion', now(), $3, $4, $5::jsonb)`,
        [
          args.traceId,
          seq,
          args.actor,
          args.personaId,
          // El motivo se guarda prefijado con la decision, y eso resuelve dos cosas a la vez.
          //
          // La visible: en la historia del caso se lee «aprobado: …» sin tener que deducirlo
          // del cambio de estado.
          //
          // La que importa: `RunLog.casos()` cuenta un escalamiento cuando el motivo EMPIEZA
          // con "escalamiento". Si una persona escribiera esa palabra como razon de su
          // decision, el plegado contaria un escalamiento que la proyeccion no tiene, y las
          // dos dejarian de cuadrar. Con el prefijo, un motivo humano nunca puede empezar asi.
          JSON.stringify({
            de: caso.estado,
            a: destino,
            motivo: `${args.resolucion === "aprobar" ? "aprobado" : "rechazado"}: ${args.motivo}`,
          }),
        ],
      );

      // La proyeccion, en la misma transaccion. `ultimo_seq` avanza con ella: es lo que hace
      // que el candado del siguiente funcione.
      //
      // `responsable` TAMBIEN se mueve, y no es cosmetico. `RunLog.casos()` pliega asi:
      //
      //     caso.responsable = evento.get("actor", caso.responsable)
      //
      // es decir, una transicion deja como responsable a quien la hizo. Si aqui no se
      // actualizara, la proyeccion se quedaria con el agente mientras el plegado devolveria
      // a la persona — y §6 dice que si la proyeccion divergiera "se tira y se vuelve a
      // plegar". Una proyeccion que no se puede reconstruir sin cambiar deja de ser una
      // proyeccion y pasa a ser una segunda verdad.
      await ejecutar(
        `update casos
            set estado = $2, actualizado_en = now(), ultimo_seq = $3, responsable = $4
          where trace_id = $1`,
        [args.traceId, destino, seq, args.actor],
      );

      return { traceId: args.traceId, estado: destino, seq };
    });
  } catch (error) {
    if (esChoqueDeSeq(error)) {
      // El otro lado del candado: la carrera que el `select ... for update` no alcanzo a
      // serializar. El mensaje es el de §8.4, y dice que paso, no "intente de nuevo".
      throw new TeGanaronDeMano(
        "Alguien resolvio este caso hace un momento. Tu decision no se guardo, y la suya " +
          "quedo registrada con su nombre. Recarga para ver quien fue.",
      );
    }
    throw error;
  }
};

// --- pausa de la oficina (vista 9) -----------------------------------------

export class PausaInvalida extends Error {}

/**
 * Pausa la oficina. Solo Direccion, y el que llama lo comprueba.
 *
 * Motivo y condicion de reanudacion son obligatorios, y no por formalismo: una pausa sin
 * condicion de levantamiento es una pausa que nadie sabe cuando termina, y dentro de un mes
 * nadie podra decir si se levanto porque se cumplio algo o porque hacia falta trabajar. El
 * esquema lo impone con `not null`; aqui se rechaza antes para poder decir cual falta.
 *
 * `pausa_activa_unica` impide dos pausas abiertas a la vez. Si ya hay una, esto falla, y
 * esta bien que falle: pausar lo ya pausado no significa nada.
 */
export const pausarOficina = async (args: {
  personaId: string;
  motivo: string;
  seReanudaCuando: string;
}): Promise<void> => {
  const motivo = args.motivo.trim();
  const condicion = args.seReanudaCuando.trim();
  if (!motivo) throw new PausaInvalida("Una pausa sin motivo escrito no es una pausa: es un olvido.");
  if (!condicion) {
    throw new PausaInvalida(
      "Falta la condicion de reanudacion. Sin ella nadie sabe que tiene que pasar para volver " +
        "a trabajar, y la pausa se levanta el dia que a alguien le urge algo.",
    );
  }

  try {
    await enTransaccion(async (ejecutar) => {
      await ejecutar(
        `insert into pausa (por, motivo, se_reanuda_cuando) values ($1, $2, $3)`,
        [args.personaId, motivo, condicion],
      );
    });
  } catch (error) {
    if (esChoqueDeSeq(error)) {
      throw new PausaInvalida("La oficina ya esta en pausa. Levantala antes de pausarla otra vez.");
    }
    throw error;
  }
};

/** Levanta la pausa activa. Exige decir por que se levanta, por la misma razon. */
export const reanudarOficina = async (args: {
  personaId: string;
  porque: string;
}): Promise<void> => {
  const porque = args.porque.trim();
  if (!porque) {
    throw new PausaInvalida(
      "Falta por que se reanuda. El levantamiento se escribe en la MISMA fila que el motivo: " +
        "si vivieran separados, en un mes nadie sabria si se cumplio la condicion o si hacia " +
        "falta trabajar.",
    );
  }

  await enTransaccion(async (ejecutar) => {
    const cambiadas = await ejecutar(
      `update pausa
          set hasta = now(), reanudada_por = $1, reanudada_porque = $2
        where hasta is null
        returning id`,
      [args.personaId, porque],
    );
    if (cambiadas.rows.length === 0) {
      throw new PausaInvalida("No hay ninguna pausa activa que levantar.");
    }
  });
};

// --- pausa de un agente (§17) ----------------------------------------------

/**
 * Pausar NO es retirar, y por eso no viven en el mismo sitio.
 *
 * Pausar es operativo y reversible: se escribe en Postgres, con motivo y condicion de
 * reanudacion obligatorios, y se hace desde el portal en dos clics. Retirar es contractual y
 * definitivo: se escribe en el YAML, pasa por PR y queda en el historial de git. Un agente
 * pausado sigue siendo `built` — simplemente hoy no trabaja.
 */
export const pausarAgente = async (args: {
  agenteId: string;
  personaId: string;
  motivo: string;
  seReanudaCuando: string;
}): Promise<void> => {
  const motivo = args.motivo.trim();
  const condicion = args.seReanudaCuando.trim();
  if (!motivo || !condicion) {
    throw new PausaInvalida(
      "Pausar un agente exige motivo y condicion de reanudacion. Un agente que nadie convoca " +
        "por descuido y uno detenido a proposito se ven igual desde fuera, y no son lo mismo.",
    );
  }

  try {
    await enTransaccion(async (ejecutar) => {
      await ejecutar(
        `insert into agente_pausa (agente, por, motivo, se_reanuda_cuando)
         values ($1, $2, $3, $4)`,
        [args.agenteId, args.personaId, motivo, condicion],
      );
    });
  } catch (error) {
    if (esChoqueDeSeq(error)) {
      throw new PausaInvalida(`${args.agenteId} ya esta pausado.`);
    }
    throw error;
  }
};

// --- convocar (vista 8) ------------------------------------------------------

export class NoSePudoConvocar extends Error {}

export interface EncargoCreado {
  id: string;
  traceId: string;
}

/**
 * Abre un encargo: la fila, su caso y los dos eventos, en UNA transaccion.
 *
 * Es la unica accion del portal que **crea** en vez de resolver, y por eso toca cuatro cosas
 * a la vez. Que vayan juntas no es comodidad: un encargo sin caso deja un `trace_id` que
 * apunta a nada, y un caso sin su evento de apertura rompe el plegado —`RunLog.casos()`
 * levanta `ErrorDeIntegridad` en cuanto ve un evento de un trace que nunca se abrio—.
 *
 * Se replica exactamente lo que escribe `office/bitacora.py:registrar(evento="convocatoria")`:
 *
 *     seq 1   apertura    tipo `encargo`, referencia = el id del encargo, criticidad segun HITL
 *     seq 2   paso        tipo `ruteo`, con las entradas de oficina que `bitacora.leer()` busca
 *
 * Si esos dos eventos no tuvieran esta forma, el encargo existiria en el portal y seria
 * invisible para el CLI. Dos verdades otra vez.
 */
export const crearEncargo = async (args: {
  agenteId: string;
  titulo: string;
  descripcion: string;
  entregableEsperado: string;
  dependeDe: string[];
  hitl: boolean;
  criticidad: "alta" | "media";
  personaId: string;
  personaNombre: string;
}): Promise<EncargoCreado> => {
  const titulo = args.titulo.trim();
  const descripcion = args.descripcion.split(/\s+/).join(" ").trim();
  const entregable = args.entregableEsperado.trim();

  try {
    return await enTransaccion(async (ejecutar) => {
      // El id y el trace se calculan DENTRO de la transaccion. Fuera, dos convocatorias
      // simultaneas leerian el mismo maximo y elegirian el mismo E-0NN.
      const ultimo = await ejecutar(
        `select coalesce(max(substring(id from 3)::int), 0) as n
           from encargos where id ~ '^E-[0-9]+$'`,
      );
      const numero = Number((ultimo.rows[0] as { n: number }).n) + 1;
      const id = `E-${String(numero).padStart(3, "0")}`;

      // El trace lleva la fecha para que sea legible y ordenable, igual que `nuevo_trace()`.
      const hoy = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const delDia = await ejecutar(
        `select count(*) as n from casos where trace_id like $1`,
        [`TR-${hoy}-%`],
      );
      const consecutivo = Number((delDia.rows[0] as { n: number }).n) + 1;
      const traceId = `TR-${hoy}-${String(consecutivo).padStart(3, "0")}`;

      // 1. La apertura del caso.
      await ejecutar(
        `insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
         values ($1, 1, 'apertura', now(), $2, $3, $4::jsonb)`,
        [
          traceId,
          args.agenteId,
          args.personaId,
          JSON.stringify({ tipo: "encargo", referencia: id, criticidad: args.criticidad }),
        ],
      );

      // 2. El paso de ruteo, con las entradas que `bitacora.leer()` busca para reconocerlo
      //    como evento de oficina. Sin `evento_oficina` el CLI no lo veria.
      await ejecutar(
        `insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
         values ($1, 2, 'paso', now(), $2, $3, $4::jsonb)`,
        [
          traceId,
          args.agenteId,
          args.personaId,
          JSON.stringify({
            span_id: `${traceId}.001`,
            parent_span_id: null,
            tipo: "ruteo",
            resultado: "ok",
            decision_ruteo: "",
            entradas: {
              evento_oficina: "convocatoria",
              encargo: id,
              autor: args.personaNombre,
              detalle: titulo,
            },
            salidas: {},
            versiones: {},
            tokens: 0,
            costo_mxn: "0.00",
            latencia_ms: 0,
            gate: {},
          }),
        ],
      );

      // 3. La proyeccion del caso. `ultimo_seq = 2` porque acabamos de escribir dos eventos:
      //    es el punto de partida del candado de §8.4 para quien lo resuelva despues.
      await ejecutar(
        `insert into casos (trace_id, tipo, referencia, criticidad, estado, responsable,
                            abierto_en, actualizado_en, pasos, ultimo_seq)
         values ($1, 'encargo', $2, $3, 'recibido', $4, now(), now(), 1, 2)`,
        [traceId, id, args.criticidad, args.agenteId],
      );

      // 4. El encargo. Va al final porque su `trace_id` es FK a `casos`.
      await ejecutar(
        `insert into encargos (id, titulo, agente, convocado_por, convocado_por_actor, estado,
                               descripcion, entregable_esperado, depende_de, hitl, trace_id)
         values ($1, $2, $3, $4, $5, 'pendiente', $6, $7, $8, $9, $10)`,
        [
          id,
          titulo,
          args.agenteId,
          args.personaId,
          args.personaNombre,
          descripcion,
          entregable,
          args.dependeDe,
          args.hitl,
          traceId,
        ],
      );

      return { id, traceId };
    });
  } catch (error) {
    if (esChoqueDeSeq(error)) {
      // Dos convocatorias en el mismo instante eligieron el mismo id o el mismo trace. La
      // segunda revierte entera; no queda un encargo a medias.
      throw new NoSePudoConvocar(
        "Otra convocatoria se registro en el mismo instante y tomo el numero. " +
          "Vuelve a intentarlo: no se creo nada.",
      );
    }
    throw error;
  }
};

// --- festivos (scripts/sql/0003) --------------------------------------------

export class FestivoInvalido extends Error {}

const ES_FECHA = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Declara un dia festivo.
 *
 * `fecha` viaja como texto "AAAA-MM-DD" de punta a punta y nunca como `Date`. Un feriado es
 * una fecha de calendario, no un instante: convertirlo a `Date` le pega el huso del proceso,
 * y el 16 de septiembre guardado desde un navegador en UTC-6 puede volver como el 15.
 *
 * `on conflict (fecha) do update` a proposito: volver a declarar un dia que ya existe es
 * corregirle el motivo o el alcance, no un error. Lo que NO se pisa es el origen manual — ver
 * `importarFestivos`.
 */
export const declararFestivo = async (args: {
  fecha: string;
  motivo: string;
  alcance: "completo" | "administrativo";
  personaId: string;
}): Promise<void> => {
  const fecha = args.fecha.trim();
  const motivo = args.motivo.trim();
  if (!ES_FECHA.test(fecha)) {
    throw new FestivoInvalido(`«${fecha}» no es una fecha AAAA-MM-DD.`);
  }
  if (!motivo) {
    throw new FestivoInvalido(
      "Escribe que se celebra. Un feriado sin motivo no se puede revisar despues: dentro de " +
        "un ano nadie sabra si sigue vigente.",
    );
  }

  await enTransaccion(async (ejecutar) => {
    await ejecutar(
      `insert into festivos (fecha, motivo, origen, alcance, declarado_por)
       values ($1::date, $2, 'manual', $3, $4)
       on conflict (fecha) do update
         set motivo = excluded.motivo,
             alcance = excluded.alcance,
             origen = 'manual',
             declarado_por = excluded.declarado_por`,
      [fecha, motivo, args.alcance, args.personaId],
    );
  });
};

export const borrarFestivo = async (fecha: string): Promise<boolean> => {
  if (!ES_FECHA.test(fecha.trim())) {
    throw new FestivoInvalido(`«${fecha}» no es una fecha AAAA-MM-DD.`);
  }
  return enTransaccion(async (ejecutar) => {
    const r = await ejecutar(`delete from festivos where fecha = $1::date returning fecha`, [
      fecha.trim(),
    ]);
    return r.rows.length > 0;
  });
};

export interface ResultadoImportacion {
  agregados: number;
  actualizados: number;
  respetados: string[];
}

/**
 * Importa una tanda de festivos de un `.ics`.
 *
 * LA REGLA QUE IMPORTA: **una importacion no pisa lo que alguien escribio a mano.** Si el 16
 * de septiembre ya esta declarado como `manual`, el archivo no lo cambia — se cuenta como
 * respetado y se dice en pantalla. Al reves seria que reimportar un calendario deshiciera en
 * silencio las correcciones de la persona que sabe cuales descansa Fleeter de verdad, que es
 * justamente el dato que el archivo no tiene.
 *
 * Todo va en UNA transaccion: media importacion es peor que ninguna, porque deja un
 * calendario que nadie sabe si esta completo.
 */
export const importarFestivos = async (args: {
  eventos: Array<{ fecha: string; motivo: string; uid: string | null }>;
  alcance: "completo" | "administrativo";
  personaId: string;
}): Promise<ResultadoImportacion> => {
  for (const e of args.eventos) {
    if (!ES_FECHA.test(e.fecha)) {
      throw new FestivoInvalido(`El archivo trae una fecha ilegible: «${e.fecha}».`);
    }
  }

  return enTransaccion(async (ejecutar) => {
    let agregados = 0;
    let actualizados = 0;
    const respetados: string[] = [];

    for (const e of args.eventos) {
      const previo = await ejecutar(`select origen, motivo from festivos where fecha = $1::date`, [
        e.fecha,
      ]);
      const existente = previo.rows[0] as { origen: string; motivo: string } | undefined;

      if (existente?.origen === "manual") {
        respetados.push(`${e.fecha} — ${existente.motivo} (declarado a mano)`);
        continue;
      }

      await ejecutar(
        `insert into festivos (fecha, motivo, origen, alcance, declarado_por, uid_externo)
         values ($1::date, $2, 'ics', $3, $4, $5)
         on conflict (fecha) do update
           set motivo = excluded.motivo,
               alcance = excluded.alcance,
               declarado_por = excluded.declarado_por,
               uid_externo = excluded.uid_externo`,
        [e.fecha, e.motivo, args.alcance, args.personaId, e.uid],
      );
      if (existente) actualizados += 1;
      else agregados += 1;
    }

    return { agregados, actualizados, respetados };
  });
};

// --- avanzar un caso hasta la bandeja ---------------------------------------

/**
 * Lo que le faltaba al ciclo: **meter un caso a la bandeja.**
 *
 * `resolverHitl` saca casos de `esperando_humano`. Nada los metia. §4 retiro
 * `office.cli avanzar` —era la unica forma de mover un encargo— y el portal no lo
 * reemplazo, asi que un encargo convocado se quedaba en `recibido` para siempre y la bandeja
 * no se llenaba nunca. El ciclo quedaba abierto justo por el lado que importa.
 *
 * El vocabulario es el del encargo, no el del caso, porque es el que usa quien trabaja:
 *
 *     empezar         pendiente -> en_curso   ·  el caso pasa a `en_proceso`
 *     mandar_a_firma  necesita una persona    ·  el caso pasa a `esperando_humano`
 *     bloquear        falta contexto          ·  el caso pasa a `bloqueado`
 *     desbloquear     ya hay contexto         ·  el caso vuelve a `en_proceso`
 *
 * Y ahi se detiene. **Cerrar el caso NO esta aqui**: eso lo hace una persona desde la
 * bandeja, que es el punto entero del portal. `office/bitacora.py` si permite un `cierre`
 * que atraviesa `esperando_humano` de corrido — en el CLI tiene sentido, porque quien lo
 * teclea ES la persona que firma. Reproducir ese atajo aqui dejaria cerrar un caso con firma
 * humana sin que ninguna persona firmara.
 */
export const AVANCES = {
  empezar: {
    desde: ["recibido"],
    a: "en_proceso",
    verbo: "empezado",
  },
  mandar_a_firma: {
    desde: ["en_proceso", "esperando_validacion"],
    a: "esperando_humano",
    verbo: "mandado a firma",
  },
  bloquear: {
    desde: ["recibido", "en_proceso", "esperando_validacion", "esperando_humano"],
    a: "bloqueado",
    verbo: "bloqueado",
  },
  desbloquear: {
    desde: ["bloqueado"],
    a: "en_proceso",
    verbo: "desbloqueado",
  },
} as const;

export type Avance = keyof typeof AVANCES;

/**
 * Mueve el caso UN paso, con el mismo candado y la misma disciplina que `resolverHitl`.
 *
 * Un paso, no un camino: `bitacora.py:_camino()` calcula la ruta mas corta y atraviesa los
 * estados intermedios de golpe. Aqui eso seria saltarse la bandeja. Cada transicion del
 * portal es la decision de alguien, y cada decision deja su evento con su autor.
 */
export const avanzarCaso = async (args: {
  traceId: string;
  avance: Avance;
  personaId: string;
  actor: string;
  motivo: string;
  ultimoSeqVisto: number;
}): Promise<Resuelto> => {
  const regla = AVANCES[args.avance];

  try {
    return await enTransaccion(async (ejecutar) => {
      const actual = await ejecutar(
        `select estado, ultimo_seq from casos where trace_id = $1 for update`,
        [args.traceId],
      );
      const caso = actual.rows[0] as { estado: string; ultimo_seq: number } | undefined;
      if (!caso) throw new TransicionInvalida(`El caso ${args.traceId} no existe.`);

      if (!(regla.desde as readonly string[]).includes(caso.estado)) {
        throw new TransicionInvalida(
          `${args.traceId} esta en ${caso.estado}: desde ahi no se puede ` +
            `${args.avance.replace(/_/g, " ")}. Se puede desde: ${regla.desde.join(", ")}.`,
        );
      }

      // La maquina de estados manda igual, aunque la regla de arriba ya lo permita. Las dos
      // tienen que estar de acuerdo, y si alguna vez discrepan gana la de `caso.py`.
      const permitidos = TRANSICIONES[caso.estado] ?? [];
      if (!permitidos.includes(regla.a)) {
        throw new TransicionInvalida(
          `${args.traceId} esta en ${caso.estado} y no puede pasar a ${regla.a}; ` +
            `permitido: ${permitidos.join(", ") || "nada, el caso ya cerro"}.`,
        );
      }

      if (caso.ultimo_seq !== args.ultimoSeqVisto) {
        throw new TeGanaronDeMano(
          `Este caso cambio mientras lo mirabas: ibas por el evento ${args.ultimoSeqVisto} ` +
            `y ya va en el ${caso.ultimo_seq}. Vuelve a cargarlo.`,
        );
      }

      const seq = caso.ultimo_seq + 1;
      await ejecutar(
        `insert into eventos (trace_id, seq, evento, ts, actor, autor_persona, datos)
         values ($1, $2, 'transicion', now(), $3, $4, $5::jsonb)`,
        [
          args.traceId,
          seq,
          args.actor,
          args.personaId,
          // Mismo prefijo que en `resolverHitl`, y por la misma razon: asi un motivo humano
          // no puede empezar con "escalamiento" y descuadrar el conteo al replegar.
          JSON.stringify({
            de: caso.estado,
            a: regla.a,
            motivo: `${regla.verbo}: ${args.motivo}`,
          }),
        ],
      );
      await ejecutar(
        `update casos
            set estado = $2, actualizado_en = now(), ultimo_seq = $3, responsable = $4
          where trace_id = $1`,
        [args.traceId, regla.a, seq, args.actor],
      );
      return { traceId: args.traceId, estado: regla.a, seq };
    });
  } catch (error) {
    if (esChoqueDeSeq(error)) {
      throw new TeGanaronDeMano(
        "Alguien movio este caso hace un momento. Tu cambio no se guardo; recarga para verlo.",
      );
    }
    throw error;
  }
};
