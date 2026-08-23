import { NextResponse } from "next/server";

import {
  FestivoInvalido,
  borrarFestivo,
  declararFestivo,
  importarFestivos,
} from "@/lib/db/escrituras";
import { leerIcs } from "@/lib/ics";
import { SinAutoridad, exigirPersona } from "@/lib/sesion";

/**
 * Declarar, importar y quitar dias festivos.
 *
 * QUIEN PUEDE. Direccion y quien opera; los externos no. La lista de feriados no es un dato
 * cosmetico: **decide cuando vencen las aprobaciones**. Un dia declarado de mas alarga todos
 * los SLA de esa semana, y uno de menos los acorta. `authority-gate.yaml` ya dice quien
 * responde por la operacion, asi que el rol se deriva de ahi y no se inventa una lista nueva.
 *
 * El archivo llega como texto en el cuerpo, no como `multipart`: un `.ics` son unos kilobytes
 * y el navegador puede leerlo antes de mandarlo, lo que ademas permite enseñar lo que se va a
 * importar **antes** de tocar la base.
 */

const ALCANCES = ["completo", "administrativo"] as const;
type Alcance = (typeof ALCANCES)[number];

const texto = (v: unknown) => (typeof v === "string" ? v.trim() : "");

async function quien() {
  const sesion = await exigirPersona();
  // Un externo (contador, abogado) entra a leer y no toca la operacion. Es la misma regla
  // dura de §11.3 que impide que apruebe un HITL.
  if (sesion.persona.rol === "externo" || sesion.persona.rol === "sin_rol") {
    throw new SinAutoridad(
      `${sesion.persona.nombre} tiene rol ${sesion.persona.rol}: el calendario laboral decide ` +
        `cuando vencen las aprobaciones, y eso lo declara quien responde por la operacion.`,
    );
  }
  return sesion;
}

export async function POST(peticion: Request) {
  let sesion;
  try {
    sesion = await quien();
  } catch (error) {
    if (error instanceof SinAutoridad) {
      return NextResponse.json({ error: error.detalle ?? error.message }, { status: 403 });
    }
    throw error;
  }

  const cuerpo = (await peticion.json().catch(() => ({}))) as Record<string, unknown>;
  const accion = texto(cuerpo.accion);
  const alcanceCrudo = texto(cuerpo.alcance) || "completo";
  if (!ALCANCES.includes(alcanceCrudo as Alcance)) {
    return NextResponse.json({ error: `Alcance desconocido: ${alcanceCrudo}.` }, { status: 400 });
  }
  const alcance = alcanceCrudo as Alcance;

  try {
    if (accion === "declarar") {
      await declararFestivo({
        fecha: texto(cuerpo.fecha),
        motivo: texto(cuerpo.motivo),
        alcance,
        personaId: sesion.personaId,
      });
      return NextResponse.json({ ok: true, por: sesion.persona.nombre });
    }

    if (accion === "borrar") {
      const habia = await borrarFestivo(texto(cuerpo.fecha));
      if (!habia) {
        return NextResponse.json({ error: "Ese dia no estaba declarado." }, { status: 404 });
      }
      return NextResponse.json({ ok: true });
    }

    if (accion === "importar") {
      const contenido = typeof cuerpo.ics === "string" ? cuerpo.ics : "";
      if (!contenido.includes("BEGIN:VEVENT")) {
        return NextResponse.json(
          { error: "El archivo no trae ningun evento. ¿Es un .ics exportado del calendario?" },
          { status: 400 },
        );
      }
      const { eventos, omitidos } = leerIcs(contenido);
      if (eventos.length === 0) {
        return NextResponse.json(
          {
            error:
              "El archivo no trae ningun evento de dia completo. Los feriados se exportan como " +
              "eventos de todo el dia; los que tienen hora se ignoran a proposito.",
            omitidos,
          },
          { status: 400 },
        );
      }
      const resultado = await importarFestivos({
        eventos,
        alcance,
        personaId: sesion.personaId,
      });
      // `omitidos` viaja siempre, aunque este vacio: una importacion que no dice lo que dejo
      // fuera se lee como una que lo trajo todo.
      return NextResponse.json({ ...resultado, omitidos, leidos: eventos.length });
    }

    return NextResponse.json(
      { error: `Accion desconocida: ${accion || "(vacia)"}. Solo declarar, importar o borrar.` },
      { status: 400 },
    );
  } catch (error) {
    if (error instanceof FestivoInvalido) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    const mensaje = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `No se pudo escribir: ${mensaje}` }, { status: 500 });
  }
}
