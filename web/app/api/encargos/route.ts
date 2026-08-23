import { NextResponse } from "next/server";

import { puedeConvocar } from "@/lib/convocar";
import { pausaActiva } from "@/lib/db/consultas";
import { NoSePudoConvocar, crearEncargo } from "@/lib/db/escrituras";
import { SinAutoridad, exigirPersona } from "@/lib/sesion";

/**
 * Convocar a un agente (vista 8). La unica accion del portal que CREA en vez de resolver.
 *
 * Las reglas viven en `lib/convocar.ts`, portadas de `agents/runtime.py` y contrastadas
 * contra el Python con vectores dorados. Aqui solo se ordenan las tres cosas que esa funcion
 * no puede hacer sola: saber quien eres, leer la pausa, y escribir.
 *
 * SOBRE LA PAUSA. Se lee de Postgres, y si NO SE PUEDE LEER se rechaza igual. Es
 * deliberado: nadie puede afirmar que la oficina este abierta si la base no respondio, y
 * convocar sobre esa suposicion es exactamente lo que la pausa impide. Los dos mensajes son
 * distintos porque mandan a hacer cosas distintas — uno a esperar, otro a revisar la base.
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
  const lista = (v: unknown) =>
    Array.isArray(v) ? v.map((x) => String(x).trim()).filter(Boolean) : [];

  const borrador = {
    agenteId: texto(cuerpo.agenteId),
    titulo: texto(cuerpo.titulo),
    descripcion: texto(cuerpo.descripcion),
    entregableEsperado: texto(cuerpo.entregableEsperado),
    hitl: Boolean(cuerpo.hitl),
  };

  const pausa = await pausaActiva();
  if (!pausa.ok) {
    return NextResponse.json(
      {
        error:
          `No se puede comprobar si la oficina esta en pausa, asi que no se convoca a nadie: ` +
          `${pausa.detalle}`,
      },
      { status: 503 },
    );
  }

  const veredicto = puedeConvocar({
    borrador,
    persona: sesion.persona,
    registro: sesion.registro,
    pausa: pausa.datos,
  });

  if (!veredicto.puede) {
    // 409 y no 400: casi todos estos «no» son sobre el estado del mundo (el agente esta
    // sin encender, la oficina esta en pausa), no sobre la forma de la peticion. El unico
    // que si es del formulario es `encargo_ambiguo`.
    const codigo = veredicto.motivo === "encargo_ambiguo" ? 400 : 409;
    return NextResponse.json(
      { error: veredicto.detalle, motivo: veredicto.motivo, faltantes: veredicto.faltantes },
      { status: codigo },
    );
  }

  try {
    const creado = await crearEncargo({
      agenteId: veredicto.agenteId,
      titulo: borrador.titulo,
      descripcion: borrador.descripcion,
      entregableEsperado: borrador.entregableEsperado,
      dependeDe: lista(cuerpo.dependeDe),
      hitl: borrador.hitl,
      criticidad: veredicto.criticidad,
      personaId: sesion.personaId,
      personaNombre: sesion.persona.nombre,
    });
    return NextResponse.json({ ...creado, convocadoPor: sesion.persona.nombre });
  } catch (error) {
    if (error instanceof NoSePudoConvocar) {
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
    const mensaje = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `No se pudo escribir: ${mensaje}` }, { status: 500 });
  }
}
