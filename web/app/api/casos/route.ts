import { NextResponse } from "next/server";

import {
  AVANCES,
  TeGanaronDeMano,
  TransicionInvalida,
  avanzarCaso,
  type Avance,
} from "@/lib/db/escrituras";
import { responsableDe } from "@/lib/rbac";
import { SinAutoridad, exigirPersona } from "@/lib/sesion";

/**
 * Mover un caso por la maquina de estados, hasta dejarlo en la bandeja.
 *
 * QUIEN PUEDE: quien responde por el equipo del agente, o Direccion. Es mas estrecho que
 * "cualquiera que vea el caso", y a proposito: mandar algo a firma consume el tiempo de
 * quien tiene que firmarlo, y bloquear un caso lo saca de la operacion. No es escribir un
 * documento propio; es mover trabajo ajeno.
 *
 * Se comprueba con `responsableDe()`, el mismo derivado que usa la bandeja — agente → equipo
 * → `owner_humano`. Una segunda lista de "quien puede mover casos" seria una segunda verdad
 * sobre autoridad, que es lo que §7 existe para no tener.
 */
export async function POST(peticion: Request) {
  let sesion;
  try {
    sesion = await exigirPersona();
  } catch (error) {
    if (error instanceof SinAutoridad) {
      return NextResponse.json({ error: error.detalle }, { status: 403 });
    }
    throw error;
  }

  const cuerpo = (await peticion.json().catch(() => ({}))) as Record<string, unknown>;
  const texto = (v: unknown) => (typeof v === "string" ? v.trim() : "");
  const traceId = texto(cuerpo.traceId);
  const avance = texto(cuerpo.avance) as Avance;
  const agenteId = texto(cuerpo.agenteId);
  const motivo = texto(cuerpo.motivo);
  const ultimoSeqVisto = Number(cuerpo.ultimoSeqVisto);

  if (!traceId || !(avance in AVANCES)) {
    return NextResponse.json(
      {
        error:
          `Avance desconocido: ${avance || "(vacio)"}. ` +
          `Validos: ${Object.keys(AVANCES).join(", ")}.`,
      },
      { status: 400 },
    );
  }
  if (!Number.isInteger(ultimoSeqVisto) || ultimoSeqVisto < 0) {
    // Sin este numero no hay candado. Recalcularlo en el servidor lo volveria teatro.
    return NextResponse.json(
      { error: "Falta el numero de evento que tenias a la vista. Recarga el caso." },
      { status: 400 },
    );
  }
  if (!motivo) {
    return NextResponse.json(
      { error: "Escribe por que. Un cambio de estado sin rastro no se puede auditar despues." },
      { status: 400 },
    );
  }

  const responsable = responsableDe(agenteId, sesion.registro);
  const esDireccion = sesion.persona.rol === "direccion";
  if (!esDireccion && sesion.persona.nombre !== responsable) {
    return NextResponse.json(
      {
        error:
          `${sesion.persona.nombre} no responde por ${agenteId || "este caso"}. ` +
          `Responde ${responsable ?? "nadie declarado"}.`,
      },
      { status: 403 },
    );
  }

  try {
    const movido = await avanzarCaso({
      traceId,
      avance,
      personaId: sesion.personaId,
      actor: sesion.persona.nombre,
      motivo,
      ultimoSeqVisto,
    });
    return NextResponse.json({ ...movido, por: sesion.persona.nombre });
  } catch (error) {
    if (error instanceof TeGanaronDeMano || error instanceof TransicionInvalida) {
      // 409 y no 400: es el estado del mundo el que no admite el movimiento, no la peticion.
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
    const mensaje = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `No se pudo escribir: ${mensaje}` }, { status: 500 });
  }
}
