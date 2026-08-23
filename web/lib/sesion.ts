/**
 * De una sesion de Clerk a una autoridad del registro (docs/portal.md §7.4).
 *
 * "Autenticado no es autorizado." Clerk responde *quien inicio sesion*; no sabe nada de
 * `authority-gate.yaml` ni de quien responde por que equipo. El puente es la tabla
 * `personas`: una fila con `clerk_user_id` y un `nombre` que existe en el gate. Sin esa fila
 * hay una cuenta valida y ninguna autoridad, y eso NO es lo mismo que no haber iniciado
 * sesion.
 *
 * TRES ESTADOS, y son tres a proposito:
 *
 *   `vinculada`     hay fila: se sabe quien es y que puede aprobar.
 *   `no_vinculada`  la base respondio y no hay fila. Es la pantalla de §7.4.
 *   `sin_verificar` no se pudo preguntar (hoy: falta la contrasena de Postgres, §15).
 *
 * El tercero existe porque colapsarlo con el segundo seria decirle a alguien "tu cuenta no
 * esta vinculada" cuando la verdad es "no pude comprobarlo". Son dos problemas distintos,
 * con dos arreglos distintos, y confundirlos manda a la persona equivocada a buscar.
 *
 * QUE PUEDE HACER CADA UNO:
 *
 *   Lectura   `vinculada` y `sin_verificar`. Las vistas de solo lectura pintan el registro,
 *             que vive en git y ya lo tiene quien tiene el repositorio. Cerrarlas cuando no
 *             hay base dejaria el portal a oscuras para todos —incluida Direccion— sin
 *             proteger nada que no estuviera ya a la vista.
 *   Escritura SOLO `vinculada`. `exigirPersona()` rechaza los otros dos. Un evento sin autor
 *             real es exactamente el hueco que este portal existe para cerrar: hoy el
 *             `--autor` del CLI es texto libre y por eso el Gate vive en el papel.
 */

import { currentUser } from "@clerk/nextjs/server";

import { fila } from "./db/cliente";
import { cargarRegistro, resolverPersona, type Persona, type Registro } from "./rbac";

export interface FilaPersona {
  id: string;
  nombre: string;
  activa: boolean;
}

export type Sesion =
  | { estado: "vinculada"; persona: Persona; personaId: string; registro: Registro }
  | { estado: "no_vinculada"; cuenta: string; motivo: string }
  | { estado: "sin_verificar"; cuenta: string; detalle: string };

const comoSeLlama = (usuario: Awaited<ReturnType<typeof currentUser>>): string => {
  if (!usuario) return "sin sesion";
  const nombre = [usuario.firstName, usuario.lastName].filter(Boolean).join(" ").trim();
  return nombre || usuario.primaryEmailAddress?.emailAddress || usuario.id;
};

export const sesion = async (): Promise<Sesion> => {
  const usuario = await currentUser();
  const cuenta = comoSeLlama(usuario);

  if (!usuario) {
    // El layout ya corrio `auth.protect()`, asi que llegar aqui sin usuario significa que
    // algo raro paso. Se trata como no verificable, nunca como autorizado.
    return { estado: "sin_verificar", cuenta, detalle: "No hay sesion de Clerk en esta peticion." };
  }

  const encontrada = await fila<FilaPersona>(
    `select id::text as id, nombre, activa from personas where clerk_user_id = $1`,
    [usuario.id],
  );

  if (!encontrada.ok) {
    return { estado: "sin_verificar", cuenta, detalle: encontrada.detalle };
  }

  if (encontrada.datos === null) {
    return {
      estado: "no_vinculada",
      cuenta,
      motivo:
        `La cuenta de Clerk existe, pero ninguna fila de \`personas\` la reclama. ` +
        `La vincula quien administra, con el id de Clerk \`${usuario.id}\`.`,
    };
  }

  if (!encontrada.datos.activa) {
    return {
      estado: "no_vinculada",
      cuenta,
      motivo: `${encontrada.datos.nombre} esta dada de baja en \`personas\` (activa = false).`,
    };
  }

  // El ROL no se lee de la base: se deriva del registro en cada peticion (§7). Una copia del
  // rol en Postgres seria una segunda verdad que nadie sincroniza el dia que cambie un
  // `owner_humano` en registry/teams/.
  const registro = cargarRegistro();
  return {
    estado: "vinculada",
    persona: resolverPersona(encontrada.datos.nombre, registro),
    personaId: encontrada.datos.id,
    registro,
  };
};

/** El error que lanza `exigirPersona`. Lo atrapan los route handlers para responder 403. */
export class SinAutoridad extends Error {
  constructor(readonly detalle: string) {
    super(detalle);
    this.name = "SinAutoridad";
  }
}

/**
 * La persona detras de esta peticion, o se acabo.
 *
 * Toda escritura pasa por aqui. `sin_verificar` tambien se rechaza: no poder comprobar quien
 * eres no es permiso para actuar, y un evento con `autor_persona` en null es un evento sin
 * auditoria.
 */
export const exigirPersona = async (): Promise<{
  persona: Persona;
  personaId: string;
  registro: Registro;
}> => {
  const s = await sesion();
  if (s.estado === "vinculada") {
    return { persona: s.persona, personaId: s.personaId, registro: s.registro };
  }
  if (s.estado === "no_vinculada") throw new SinAutoridad(s.motivo);
  throw new SinAutoridad(
    `No se puede comprobar quien eres, asi que no se puede registrar quien actuo: ${s.detalle}`,
  );
};
