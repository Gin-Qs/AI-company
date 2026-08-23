import { NextResponse } from "next/server";

import { PausaInvalida, pausarOficina, reanudarOficina } from "@/lib/db/escrituras";
import { SinAutoridad, exigirPersona } from "@/lib/sesion";

/**
 * Pausar y reanudar la oficina. El control de maximo privilegio del sistema.
 *
 * SOLO DIRECCION, y se comprueba aqui. El rol se deriva del registro en cada peticion
 * (`autoridades.direccion` en `authority-gate.yaml`): si manana Direccion cambia de manos,
 * cambia quien puede pausar sin tocar una linea de codigo ni una fila de la base.
 *
 * POR QUE LA PAUSA VIVE EN POSTGRES Y NO EN GIT. Se considero dejarla en el YAML —es el
 * control que menos se escribe— y se descarto: `agents/runtime.py:convocar()` lee
 * `office/pausa.yaml` en cada convocatoria, y si el portal pausara en Postgres mientras el
 * runtime lee un archivo, LA PAUSA NO PAUSARIA. Dos verdades sobre el control mas importante
 * del sistema es exactamente el error que este portal existe para evitar.
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

  if (sesion.persona.rol !== "direccion") {
    return NextResponse.json(
      {
        error:
          `Pausar la oficina es de Direccion. ${sesion.persona.nombre} tiene rol ` +
          `${sesion.persona.rol} segun authority-gate.yaml.`,
      },
      { status: 403 },
    );
  }

  const cuerpo = (await peticion.json().catch(() => ({}))) as Record<string, unknown>;
  const texto = (v: unknown) => (typeof v === "string" ? v.trim() : "");
  const accion = texto(cuerpo.accion);

  try {
    if (accion === "pausar") {
      await pausarOficina({
        personaId: sesion.personaId,
        motivo: texto(cuerpo.motivo),
        seReanudaCuando: texto(cuerpo.seReanudaCuando),
      });
      return NextResponse.json({ estado: "pausada", por: sesion.persona.nombre });
    }
    if (accion === "reanudar") {
      await reanudarOficina({ personaId: sesion.personaId, porque: texto(cuerpo.porque) });
      return NextResponse.json({ estado: "activa", por: sesion.persona.nombre });
    }
    return NextResponse.json(
      { error: `Accion desconocida: ${accion || "(vacia)"}. Solo pausar o reanudar.` },
      { status: 400 },
    );
  } catch (error) {
    if (error instanceof PausaInvalida) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    const mensaje = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `No se pudo escribir: ${mensaje}` }, { status: 500 });
  }
}
