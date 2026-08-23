import { NextResponse } from "next/server";

import { puedeAprobar } from "@/lib/rbac";
import {
  DESTINO,
  TeGanaronDeMano,
  TransicionInvalida,
  resolverHitl,
  type Resolucion,
} from "@/lib/db/escrituras";
import { SinAutoridad, exigirPersona } from "@/lib/sesion";

/**
 * Resolver un HITL. La unica puerta por la que una aprobacion entra al registro (§12).
 *
 * Todo lo que decide aqui se decide **en el servidor**: quien eres, si puedes, si el caso
 * admite la transicion y si alguien te gano. Los botones de la pantalla se pintan con las
 * mismas reglas, y eso es comodidad, no seguridad — un chequeo del cliente lo quita
 * cualquiera con las herramientas del navegador. Si esta ruta confiara en lo que le mandan,
 * el Gate de Autoridad volveria a ser un documento.
 *
 * El orden de las comprobaciones importa y es de mas barato a mas caro, pero sobre todo de
 * mas general a mas especifico: quien eres, que pediste, si puedes, y solo entonces se abre
 * una transaccion.
 */

interface Cuerpo {
  traceId?: unknown;
  agenteId?: unknown;
  resolucion?: unknown;
  motivo?: unknown;
  umbral?: unknown;
  ultimoSeqVisto?: unknown;
}

const texto = (v: unknown): string => (typeof v === "string" ? v.trim() : "");

export async function POST(peticion: Request) {
  // 1. Quien eres. `sin_verificar` se rechaza igual que `no_vinculada`: no poder comprobar
  //    quien eres no es permiso para actuar, y un evento sin autor no es auditable.
  let sesion;
  try {
    sesion = await exigirPersona();
  } catch (error) {
    if (error instanceof SinAutoridad) {
      return NextResponse.json({ error: error.detalle }, { status: 403 });
    }
    throw error;
  }

  // 2. Que pediste. Nada de esto se toma por bueno: viene del navegador.
  const cuerpo = (await peticion.json().catch(() => ({}))) as Cuerpo;
  const traceId = texto(cuerpo.traceId);
  const agenteId = texto(cuerpo.agenteId);
  const resolucion = texto(cuerpo.resolucion) as Resolucion;
  const motivo = texto(cuerpo.motivo);
  const umbral = texto(cuerpo.umbral) || undefined;
  const ultimoSeqVisto = Number(cuerpo.ultimoSeqVisto);

  if (!traceId || !agenteId) {
    return NextResponse.json({ error: "Falta el caso o el agente." }, { status: 400 });
  }
  if (!(resolucion in DESTINO)) {
    return NextResponse.json(
      { error: `Resolucion desconocida: ${resolucion || "(vacia)"}. Solo aprobar o rechazar.` },
      { status: 400 },
    );
  }
  if (!Number.isInteger(ultimoSeqVisto) || ultimoSeqVisto < 0) {
    // Sin este numero no hay candado (§8.4). Aceptar la peticion sin el y recalcularlo en el
    // servidor haria que dos aprobaciones simultaneas se sobrescribieran en silencio.
    return NextResponse.json(
      { error: "Falta el numero de evento que tenias a la vista. Recarga la bandeja." },
      { status: 400 },
    );
  }
  // Rechazar sin decir por que deja un "no" sin razon en el registro, y dentro de un mes
  // nadie puede reconstruir la decision. Aprobar tambien lo pide, por simetria: la firma es
  // lo que se audita.
  if (!motivo) {
    return NextResponse.json(
      { error: "Escribe por que. Una decision sin motivo no se puede auditar despues." },
      { status: 400 },
    );
  }

  // 3. Si puedes. Se recalcula con el registro de git, no con lo que diga el cliente.
  const decision = puedeAprobar({
    persona: sesion.persona,
    agenteId,
    umbral,
    registro: sesion.registro,
  });
  if (!decision.puede) {
    return NextResponse.json({ error: decision.motivo }, { status: 403 });
  }

  // 4. Escribir.
  try {
    const resuelto = await resolverHitl({
      traceId,
      resolucion,
      personaId: sesion.personaId,
      // El actor del evento es la PERSONA, no el agente: esta transicion la hizo ella.
      actor: sesion.persona.nombre,
      motivo,
      ultimoSeqVisto,
    });
    return NextResponse.json({ ...resuelto, decidio: sesion.persona.nombre, porque: decision.motivo });
  } catch (error) {
    if (error instanceof TeGanaronDeMano) {
      // 409, no 500. Es el resultado normal de dos personas trabajando a la vez, no un fallo.
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
    if (error instanceof TransicionInvalida) {
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
    const mensaje = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `No se pudo escribir: ${mensaje}` }, { status: 500 });
  }
}
