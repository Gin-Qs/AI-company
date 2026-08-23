/**
 * Las reglas de `agents/runtime.py:convocar()`, portadas (docs/portal.md, vista 8).
 *
 * Lo que hace este modulo, en una linea: **aplica las reglas antes de que se cree nada.**
 *
 * El riesgo de este puerto no es que falle: es que funcione *casi* igual. Una regla que se
 * relaja al traducirla no truena — deja convocar a un agente que el CLI habria rechazado, y
 * el sistema queda con dos respuestas a "¿se puede convocar a D4-03?". Por eso el orden de
 * las comprobaciones es el mismo que en Python, y por eso cada una devuelve un motivo
 * escrito en vez de un booleano: la pantalla tiene que poder decir *por que* no.
 *
 * LOS TRES «NO» QUE NO SON EL MISMO. Python distingue `AgenteRetirado`, `AgenteSinEncender`
 * y `AgenteNoDisponible` a proposito, y aqui tambien:
 *
 *   retirado   no espera nada. Decirle "todavia no" a alguien cuyo agente se dio de baja
 *              hace tres meses lo manda a esperar algo que no va a pasar.
 *   listo      espera condiciones concretas, con dueno y fecha. Se enumeran.
 *   planned    espera su fase. Adelantarlo es una decision de Direccion.
 *
 * Este modulo NO escribe. Decide. Lo que escribe es `lib/db/escrituras.ts`, y solo despues
 * de que esto diga que si.
 */

import type { Agente, CondicionEncendido } from "./registro";
import type { Persona, Registro } from "./rbac";

export type MotivoRechazo =
  | "oficina_en_pausa"
  | "agente_desconocido"
  | "agente_retirado"
  | "agente_sin_encender"
  | "agente_no_disponible"
  | "consultor_con_acciones"
  | "permiso_denegado"
  | "encargo_ambiguo";

export interface Rechazo {
  puede: false;
  motivo: MotivoRechazo;
  detalle: string;
  /** Lo que falta, cuando se puede enumerar: condiciones de encendido o campos vacios. */
  faltantes?: string[];
}

export interface Permitido {
  puede: true;
  agenteId: string;
  /** Un encargo que necesita firma humana entra como caso critico (§7.3). */
  criticidad: "alta" | "media";
}

export type Veredicto = Permitido | Rechazo;

export interface Pausa {
  activa: boolean;
  desde?: string;
  por?: string;
  motivo?: string;
  seReanudaCuando?: string;
}

export interface Borrador {
  agenteId: string;
  titulo: string;
  descripcion: string;
  entregableEsperado: string;
  hitl: boolean;
}

const vacio = (v: string): boolean => !v.trim();

/**
 * ¿Se puede abrir este encargo?
 *
 * `pausa` se pasa por parametro y no se lee aqui: la fuente es Postgres (§4) y este modulo
 * tiene que poder probarse sin base de datos. Quien llama la trae; quien llama tambien se
 * asegura de que **no poder leerla** sea un error y no un `{activa: false}` inventado.
 */
export const puedeConvocar = (args: {
  borrador: Borrador;
  persona: Persona;
  registro: Registro;
  pausa: Pausa;
}): Veredicto => {
  const { borrador, persona, registro, pausa } = args;

  // 1. La pausa gana sobre todo. Mientras este activa, el runtime rechaza TODA convocatoria.
  if (pausa.activa) {
    return {
      puede: false,
      motivo: "oficina_en_pausa",
      detalle:
        `La oficina esta en pausa desde ${pausa.desde ?? "sin fecha"} por ` +
        `${pausa.por ?? "sin declarar"}: ${pausa.motivo ?? "sin motivo"}. ` +
        `Se reanuda cuando: ${pausa.seReanudaCuando ?? "sin condicion declarada"}`,
    };
  }

  const agente: Agente | undefined = registro.agentes[borrador.agenteId];
  if (!agente) {
    return {
      puede: false,
      motivo: "agente_desconocido",
      detalle: `${borrador.agenteId} no existe en el registro.`,
    };
  }

  // 2. El retiro se comprueba antes que nada mas: un agente dado de baja no tiene
  //    condiciones pendientes ni fase por llegar. No hay nada que esperar.
  if (agente.retirado) {
    const r = agente.retiro ?? {};
    return {
      puede: false,
      motivo: "agente_retirado",
      detalle:
        `${agente.id} fue retirado el ${r.fecha ?? "sin fecha"} por ${r.por ?? "sin responsable"}: ` +
        `${r.motivo ?? "sin motivo declarado"} Su trabajo lo cubre ahora: ${r.lo_cubre ?? "nadie declarado"}. ` +
        `Su historia sigue en el registro; lo que no vuelve es el agente.`,
    };
  }

  // 3. `listo` es distinto de `planned`, y la diferencia tiene dueno y fecha.
  if (agente.listo) {
    const pendientes: CondicionEncendido[] = agente.condicionesEncendido.filter(
      (c: CondicionEncendido) => !c.cumplida,
    );
    return {
      puede: false,
      motivo: "agente_sin_encender",
      detalle:
        `${agente.id} esta listo pero sin encender: faltan ${pendientes.length} de ` +
        `${agente.condicionesEncendido.length} condiciones.`,
      faltantes: pendientes.map(
        (c: CondicionEncendido) => `${c.condicion} (lo cierra ${c.responsable || "sin responsable"})`,
      ),
    };
  }

  if (!agente.disponible) {
    return {
      puede: false,
      motivo: "agente_no_disponible",
      detalle:
        `${agente.id} esta ${agente.estado}: su fase no ha llegado. Adelantarlo es una ` +
        `decision de Direccion y se escribe en el registro.`,
    };
  }

  // 4. Regla dura de §5-bis.1: si un consultor necesitara un ACT-*, el trabajo no es de
  //    consultoria. Se verifica en cada convocatoria, no solo en el validador — un control
  //    que solo corre en CI no protege la operacion.
  if (agente.tipo === "consultor" && agente.acciones.length > 0) {
    return {
      puede: false,
      motivo: "consultor_con_acciones",
      detalle:
        `${agente.id} declara acciones ${agente.acciones.join(", ")}: un consultor no ejecuta jamas.`,
    };
  }

  // 5. Quien puede convocar a quien. Lista vacia = cualquiera, igual que en Python.
  if (agente.invocablePor.length > 0 && !agente.invocablePor.includes(persona.nombre)) {
    return {
      puede: false,
      motivo: "permiso_denegado",
      detalle:
        `${persona.nombre} no puede convocar a ${agente.id}; solo pueden: ` +
        `${agente.invocablePor.join(", ")}.`,
    };
  }

  // 6. Un encargo ambiguo no arranca. El agente pide contexto, no lo inventa.
  const faltantes = [
    ["titulo", borrador.titulo],
    ["descripcion", borrador.descripcion],
    ["entregable", borrador.entregableEsperado],
  ]
    .filter(([, valor]) => vacio(valor as string))
    .map(([campo]) => campo as string);

  if (faltantes.length > 0) {
    return {
      puede: false,
      motivo: "encargo_ambiguo",
      detalle:
        `Encargo incompleto para ${agente.id}: falta ${faltantes.join(", ")}. Un encargo lleva ` +
        `que modulo, que problema y que restriccion (§5-bis.3.2).`,
      faltantes,
    };
  }

  return {
    puede: true,
    agenteId: agente.id,
    // Un encargo con firma humana entra como caso critico: su SLA en la bandeja se mide en
    // horas habiles, no en dias.
    criticidad: borrador.hitl ? "alta" : "media",
  };
};

/** A quien puede convocar esta persona hoy, para no ofrecerle en la pantalla lo que no puede. */
export const convocablesPor = (persona: Persona, registro: Registro): Agente[] =>
  Object.values(registro.agentes)
    .filter((a) => !a.retirado && a.disponible)
    .filter((a) => a.invocablePor.length === 0 || a.invocablePor.includes(persona.nombre))
    .sort((a, b) => a.id.localeCompare(b.id));
