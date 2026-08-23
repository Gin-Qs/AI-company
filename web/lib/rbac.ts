/**
 * De una cuenta de Clerk a una autoridad. Derivado, nunca guardado.
 *
 * El rol NO vive en la base de datos. Se recalcula en cada request cruzando el nombre de
 * la persona contra dos archivos que ya existen en git:
 *
 *     registry/policies/authority-gate.yaml   quien es quien, y quien aprueba que umbral
 *     registry/teams/*.yaml                   owner_humano y co_owners de cada equipo
 *
 * Una copia del rol en Postgres seria una segunda verdad que nadie sincroniza el dia que
 * cambie un owner en el registro. La cadena completa:
 *
 *     Clerk userId -> personas.nombre -> autoridades  -> rol
 *                                    -> equipos       -> alcance
 *     caso.actor (agente) -> agente.teams -> equipo -> owner_humano -> a quien le llega
 *
 * SOBRE §7.2. Hasta v3.0.1 el ruteo era `owner_humano_del_equipo` a secas, y contradecia
 * la tabla de umbrales del propio gate: Ana aprueba descuentos de hasta 5% y plazos de
 * hasta 45 dias —ambos dominio de D4-03— pero D4-03 pertenece a T04-03, cuyo owner es
 * Gabriel. Ana SI responde por otros equipos (T04-04, T07-01, T07-05); lo que pasa es que
 * los agentes de esos tres son de fases futuras y todavia no existen, asi que hoy ningun
 * HITL le llega. Ahora el ruteo es configuracion (`hitl.ruteo`), y la
 * politica vigente separa dos preguntas distintas: quien RESPONDE por el caso (uno solo) y
 * quien puede APROBARLO (el responsable, mas los co_owners a quienes el gate faculta para
 * el umbral que se disparo).
 */

import { readFileSync } from "node:fs";

import { parse } from "yaml";

import { cargarAgentes, cargarEquipos, type Agente, type Equipo } from "./registro";
import { desdeRaiz } from "./rutas";

export const rutaGate = (): string => desdeRaiz("registry", "policies", "authority-gate.yaml");

export type Rol = "direccion" | "operador" | "externo" | "sin_rol";

export type ApruebanAdemas = "nadie" | "co_owners" | "co_owners_con_autoridad";

export interface Ruteo {
  responsable: string;
  apruebanAdemas: ApruebanAdemas;
  comodinDireccion: boolean;
}

export interface Gate {
  /** Nombre de quien ejerce la Direccion. Aprueba fuera de rango y firma contratos. */
  direccion: string;
  /** dominio -> nombre. Por ejemplo { finanzas: "Nay", comercial_ops: "Ana" }. */
  operadores: Record<string, string>;
  /** Etiquetas de puesto, no personas: contador, abogado. Sin autoridad de aprobacion. */
  externos: string[];
  /** umbral -> quienes lo pueden aprobar, en cualquier rango. */
  autoridadPorUmbral: Record<string, string[]>;
  ruteo: Ruteo;
}

export const cargarGate = (ruta: string = rutaGate()): Gate => {
  const datos = (parse(readFileSync(ruta, "utf-8")) ?? {}) as Record<string, any>;
  const autoridades = datos.autoridades ?? {};

  const operadores: Record<string, string> = {};
  for (const [dominio, valor] of Object.entries(autoridades as Record<string, any>)) {
    if (dominio === "direccion" || dominio === "externos") continue;
    if (typeof valor === "string") operadores[dominio] = valor;
  }

  // Quien aparece nombrado en cada umbral, venga de humano_operativo, direccion o administra.
  const autoridadPorUmbral: Record<string, string[]> = {};
  for (const [umbral, regla] of Object.entries((datos.umbrales ?? {}) as Record<string, any>)) {
    const quienes = new Set<string>();
    for (const rango of ["humano_operativo", "direccion", "administra"]) {
      const quien = (regla as any)?.[rango]?.quien;
      if (typeof quien === "string" && quien.trim()) quienes.add(quien.trim());
    }
    autoridadPorUmbral[umbral] = [...quienes];
  }

  const crudo = datos.hitl?.ruteo;
  // Compatibilidad con la forma vieja (`ruteo: owner_humano_del_equipo`), por si alguien
  // revierte el YAML: se degrada al comportamiento mas estricto, no al mas permisivo.
  const ruteo: Ruteo =
    typeof crudo === "string"
      ? { responsable: crudo, apruebanAdemas: "nadie", comodinDireccion: false }
      : {
          responsable: String(crudo?.responsable ?? "owner_humano_del_equipo"),
          apruebanAdemas: (crudo?.aprueban_ademas ?? "nadie") as ApruebanAdemas,
          comodinDireccion: Boolean(crudo?.comodin_direccion),
        };

  return {
    direccion: String(autoridades.direccion ?? ""),
    operadores,
    externos: Array.isArray(autoridades.externos)
      ? autoridades.externos.map((x: unknown) => String(x))
      : [],
    autoridadPorUmbral,
    ruteo,
  };
};

// --- la persona -------------------------------------------------------------

export interface Persona {
  nombre: string;
  rol: Rol;
  /** Equipos donde es `owner_humano`: responde por ellos y recibe sus HITL. */
  equiposResponsable: string[];
  /** Equipos donde es `co_owner`: los ve, y su autoridad depende de la politica. */
  equiposApoyo: string[];
  /** Umbrales del gate donde aparece nombrada. */
  umbralesConAutoridad: string[];
}

export interface Registro {
  agentes: Record<string, Agente>;
  equipos: Record<string, Equipo>;
  gate: Gate;
}

export const cargarRegistro = (): Registro => ({
  agentes: cargarAgentes(),
  equipos: cargarEquipos(),
  gate: cargarGate(),
});

export const resolverPersona = (nombre: string, reg: Registro): Persona => {
  const { equipos, gate } = reg;
  const equiposResponsable = Object.values(equipos)
    .filter((e) => e.ownerHumano === nombre)
    .map((e) => e.id)
    .sort();
  const equiposApoyo = Object.values(equipos)
    .filter((e) => e.coOwners.includes(nombre))
    .map((e) => e.id)
    .sort();

  let rol: Rol = "sin_rol";
  if (nombre === gate.direccion) rol = "direccion";
  else if (gate.externos.includes(nombre)) rol = "externo";
  else if (Object.values(gate.operadores).includes(nombre)) rol = "operador";

  return {
    nombre,
    rol,
    equiposResponsable,
    equiposApoyo,
    umbralesConAutoridad: Object.entries(gate.autoridadPorUmbral)
      .filter(([, quienes]) => quienes.includes(nombre))
      .map(([umbral]) => umbral)
      .sort(),
  };
};

// --- a quien le llega un HITL ----------------------------------------------

/**
 * Quien RESPONDE por un caso de este agente. Uno solo, siempre: la responsabilidad
 * compartida entre tres es responsabilidad de nadie.
 */
export const responsableDe = (agenteId: string, reg: Registro): string | null => {
  const agente = reg.agentes[agenteId];
  if (!agente) return null;
  for (const equipoId of agente.equipos) {
    const equipo = reg.equipos[equipoId];
    if (equipo?.ownerHumano) return equipo.ownerHumano;
  }
  return null;
};

export interface Decision {
  puede: boolean;
  /** Por que si o por que no, en una frase que se pueda enseñar en pantalla. */
  motivo: string;
}

/**
 * ¿Puede esta persona aprobar el HITL de este agente?
 *
 * `umbral` es el que disparo el gate (por ejemplo `descuento_tarifa`). Sin el, la politica
 * `co_owners_con_autoridad` no puede conceder nada: no se aprueba lo que no se sabe que es.
 */
export const puedeAprobar = (args: {
  persona: Persona;
  agenteId: string;
  umbral?: string;
  registro: Registro;
}): Decision => {
  const { persona, agenteId, umbral, registro } = args;
  const { gate } = registro;
  const agente = registro.agentes[agenteId];

  if (!agente) {
    return { puede: false, motivo: `${agenteId} no existe en el registro.` };
  }

  // Regla dura de §11.3: "Ningun externo (contador, abogado) tiene autoridad de aprobacion
  // en el Gate." Se comprueba explicitamente aunque por construccion no sean owner de
  // nada: un control de seguridad que solo se cumple por accidente no es un control.
  if (persona.rol === "externo") {
    return {
      puede: false,
      motivo: `${persona.nombre} es externo: sin autoridad de aprobacion en el Gate (regla dura §11.3).`,
    };
  }

  const responsable = responsableDe(agenteId, registro);
  if (persona.nombre === responsable) {
    return {
      puede: true,
      motivo: `${persona.nombre} responde por el equipo de ${agenteId}.`,
    };
  }

  if (gate.ruteo.comodinDireccion && persona.rol === "direccion") {
    return {
      puede: true,
      motivo: `${persona.nombre} ejerce la Direccion: puede aprobar cualquier HITL.`,
    };
  }

  const esCoOwner = agente.equipos.some((id) => persona.equiposApoyo.includes(id));

  switch (gate.ruteo.apruebanAdemas) {
    case "co_owners":
      if (esCoOwner) {
        return { puede: true, motivo: `${persona.nombre} es co-owner del equipo de ${agenteId}.` };
      }
      break;

    case "co_owners_con_autoridad":
      if (!esCoOwner) break;
      if (!umbral) {
        return {
          puede: false,
          motivo:
            `${persona.nombre} es co-owner del equipo de ${agenteId}, pero este HITL no declara ` +
            `que umbral disparo. Sin saber que se aprueba, no se aprueba.`,
        };
      }
      if (persona.umbralesConAutoridad.includes(umbral)) {
        return {
          puede: true,
          motivo: `${persona.nombre} es co-owner y el gate la faculta para ${umbral}.`,
        };
      }
      return {
        puede: false,
        motivo:
          `${persona.nombre} es co-owner del equipo de ${agenteId}, pero el gate no la faculta ` +
          `para ${umbral}. Eso lo aprueba ${responsable ?? "el owner del equipo"}.`,
      };

    case "nadie":
    default:
      break;
  }

  return {
    puede: false,
    motivo:
      `${persona.nombre} no tiene autoridad sobre ${agenteId}. ` +
      `Responde ${responsable ?? "nadie declarado"}.`,
  };
};

/** Los agentes cuyos HITL le llegan a esta persona, para armar su bandeja. */
export const agentesDe = (persona: Persona, reg: Registro): string[] => {
  const suyos = new Set<string>();
  const equiposVisibles = new Set([...persona.equiposResponsable, ...persona.equiposApoyo]);
  for (const agente of Object.values(reg.agentes)) {
    if (agente.tipo !== "dominio") continue;
    if (agente.equipos.some((e) => equiposVisibles.has(e))) suyos.add(agente.id);
  }
  // La Direccion ve la operacion entera: si no, un caso sin owner disponible se queda sin
  // nadie que lo mire, que es justo lo que el comodin existe para evitar.
  if (reg.gate.ruteo.comodinDireccion && persona.rol === "direccion") {
    for (const a of Object.values(reg.agentes)) {
      if (a.tipo === "dominio") suyos.add(a.id);
    }
  }
  return [...suyos].sort();
};
