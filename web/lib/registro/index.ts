/**
 * El registro, leido desde TypeScript. Solo lectura, siempre.
 *
 * Estos son los mismos archivos que lee `agents/perfiles.py`. El portal NO los escribe:
 * `registry/` cambia por PR, se valida con las reglas de `scripts/validate_registry.py`
 * y se audita en el historial de git. Un contrato que se puede cambiar desde una pantalla
 * es un contrato sin auditoria.
 *
 * En Vercel el directorio raiz del proyecto es `web/`, asi que estos archivos quedan fuera
 * del bundle salvo que `next.config.ts` los incluya con `outputFileTracingIncludes`.
 * Sin eso, esto compila en local y devuelve "archivo no encontrado" en produccion.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { parse } from "yaml";

import { desdeRaiz } from "../rutas";

export const RUTAS = {
  get agentes() {
    return desdeRaiz("registry", "agents");
  },
  get consultores() {
    return desdeRaiz("registry", "consultants");
  },
  get equipos() {
    return desdeRaiz("registry", "teams");
  },
  get identidades() {
    return desdeRaiz("office", "identidades.yaml");
  },
} as const;

/**
 * El ciclo de vida de un agente de dominio. Espejo de `agents/perfiles.py:ESTADOS`.
 *
 * La pausa NO esta aqui: es operativa, reversible y vive en la base de datos
 * (tabla `agente_pausa`). Un agente pausado sigue siendo `built`; hoy no trabaja.
 */
export const ESTADOS = ["planned", "listo", "built", "retirado"] as const;
export type Estado = (typeof ESTADOS)[number];

export interface CondicionEncendido {
  condicion: string;
  responsable: string;
  decide?: string;
  cumplida: boolean;
  donde?: string;
}

export interface Retiro {
  fecha?: string;
  por?: string;
  motivo?: string;
  lo_cubre?: string;
}

export interface Identidad {
  nombre: string;
  puesto: string;
  lema: string;
  voz: string;
  zona: string;
  escritorio: { x: number; y: number };
  sprite: Record<string, string>;
}

export interface Agente {
  id: string;
  tipo: "dominio" | "consultor";
  nombre: string;                 // el puesto
  mision: string;
  departamento: string;
  equipos: string[];
  estado: Estado | "disponible";  // los consultores no tienen fase que los encienda
  fase: number | null;
  modelTier: string;
  invocablePor: string[];
  herramientas: string[];
  herramientasPlaneadas: string[];
  entradas: string[];
  salidas: string[];
  acciones: string[];             // ACT-*
  controles: string[];            // CTL-*
  limites: string[];
  condicionesEncendido: CondicionEncendido[];
  retiro: Retiro | null;
  prompt: string | null;
  identidad: Identidad | null;
  /** Se puede convocar hoy. Un consultor, siempre (§5-bis.3.6). */
  disponible: boolean;
  listo: boolean;
  retirado: boolean;
}

export interface Equipo {
  id: string;
  nombre: string;
  departamento: string;
  ownerHumano: string;
  coOwners: string[];
  ownerDigital: string | null;
  agentes: string[];
}

const lista = (v: unknown): string[] =>
  Array.isArray(v) ? v.map((x) => String(x)) : [];

const leerYaml = (ruta: string): Record<string, any> =>
  (parse(readFileSync(ruta, "utf-8")) ?? {}) as Record<string, any>;

const yamlsDe = (carpeta: string): Record<string, any>[] =>
  readdirSync(carpeta)
    .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
    .sort()
    .map((f) => leerYaml(join(carpeta, f)));

// --- identidades ------------------------------------------------------------

export interface Zonas {
  [clave: string]: { nombre: string; descripcion: string };
}

export const cargarIdentidades = (
  ruta: string = RUTAS.identidades,
): { zonas: Zonas; agentes: Record<string, Identidad> } => {
  const datos = leerYaml(ruta);
  const agentes: Record<string, Identidad> = {};
  for (const [id, d] of Object.entries((datos.agentes ?? {}) as Record<string, any>)) {
    agentes[id] = {
      nombre: String(d.nombre ?? id),
      puesto: String(d.puesto ?? ""),
      lema: String(d.lema ?? ""),
      voz: String(d.voz ?? ""),
      zona: String(d.zona ?? ""),
      escritorio: { x: Number(d.escritorio?.x ?? 0), y: Number(d.escritorio?.y ?? 0) },
      sprite: (d.sprite ?? {}) as Record<string, string>,
    };
  }
  return { zonas: (datos.zonas ?? {}) as Zonas, agentes };
};

// --- agentes ----------------------------------------------------------------

export const cargarAgentes = (rutas: { agentes: string; consultores: string; identidades: string } = RUTAS): Record<string, Agente> => {
  const identidades = cargarIdentidades(rutas.identidades).agentes;
  const todos: Record<string, Agente> = {};

  // Consultores. No tienen fase ni estado de encendido: existen desde que el registro
  // los declara (§5-bis.3, regla 6). Y no tienen ACT-* jamas: es regla dura.
  for (const d of yamlsDe(rutas.consultores)) {
    const id = String(d.consultant_id ?? "");
    if (!id) continue;
    todos[id] = {
      id,
      tipo: "consultor",
      nombre: String(d.nombre ?? id),
      mision: lista(d.se_convoca_para).join(". "),
      departamento: "",
      equipos: [],
      estado: "disponible",
      fase: null,
      modelTier: String(d.model_tier ?? ""),
      invocablePor: lista(d.invocable_por),
      herramientas: [],
      herramientasPlaneadas: [],
      entradas: [],
      salidas: lista(d.se_convoca_para),
      acciones: lista(d.acciones_act),
      controles: [],
      limites: lista(d.no_hace),
      condicionesEncendido: [],
      retiro: null,
      prompt: `agents/prompts/${id}.md`,
      identidad: identidades[id] ?? null,
      disponible: true,
      listo: false,
      retirado: false,
    };
  }

  for (const d of yamlsDe(rutas.agentes)) {
    const id = String(d.id ?? "");
    if (!id) continue;
    const estado = String(d.estado ?? "planned") as Estado;
    todos[id] = {
      id,
      tipo: "dominio",
      nombre: String(d.name ?? id),
      mision: String(d.mission ?? "").trim(),
      departamento: String(d.department ?? ""),
      equipos: lista(d.teams),
      estado,
      fase: d.fase == null ? null : Number(d.fase),
      modelTier: String(d.model_tier ?? ""),
      invocablePor: lista(d.invocable_por),
      herramientas: lista(d.tools),
      herramientasPlaneadas: lista(d.tools_planeadas),
      entradas: lista(d.inputs),
      salidas: lista(d.outputs),
      acciones: lista(d.actions),
      controles: lista(d.controls),
      limites: lista(d.limits),
      condicionesEncendido: (Array.isArray(d.condiciones_encendido)
        ? d.condiciones_encendido
        : []
      ).map((c: any) => ({
        condicion: String(c?.condicion ?? ""),
        responsable: String(c?.responsable ?? ""),
        decide: c?.decide ? String(c.decide) : undefined,
        cumplida: Boolean(c?.cumplida),
        donde: c?.donde ? String(c.donde) : undefined,
      })),
      retiro: d.retiro ? (d.retiro as Retiro) : null,
      prompt: d.prompt ? String(d.prompt) : null,
      identidad: identidades[id] ?? null,
      disponible: estado === "built",
      listo: estado === "listo",
      retirado: estado === "retirado",
    };
  }

  return todos;
};

// --- equipos ----------------------------------------------------------------

export const cargarEquipos = (carpeta: string = RUTAS.equipos): Record<string, Equipo> => {
  const todos: Record<string, Equipo> = {};
  for (const d of yamlsDe(carpeta)) {
    const id = String(d.team_id ?? "");
    if (!id) continue;
    todos[id] = {
      id,
      nombre: String(d.nombre ?? id),
      departamento: String(d.departamento ?? ""),
      ownerHumano: String(d.owner_humano ?? ""),
      coOwners: lista(d.co_owners),
      ownerDigital: d.owner_digital ? String(d.owner_digital) : null,
      agentes: lista(d.agentes),
    };
  }
  return todos;
};

// --- lo que el resumen necesita ---------------------------------------------

export interface Panorama {
  total: number;
  disponibles: number;
  listos: number;
  planeados: number;
  retirados: number;
  consultores: number;
  /** Lo que falta para encender a los agentes `listo`, con dueño. */
  condicionesPendientes: Array<{ agente: string; condicion: string; responsable: string }>;
}

export const panorama = (agentes: Record<string, Agente>): Panorama => {
  const dominio = Object.values(agentes).filter((a) => a.tipo === "dominio");
  return {
    total: dominio.length,
    disponibles: dominio.filter((a) => a.disponible).length,
    listos: dominio.filter((a) => a.listo).length,
    planeados: dominio.filter((a) => a.estado === "planned").length,
    retirados: dominio.filter((a) => a.retirado).length,
    consultores: Object.values(agentes).filter((a) => a.tipo === "consultor").length,
    // Un agente `listo` es una situacion legitima y peligrosa: el trabajo esta hecho,
    // nadie lo usa y la razon se olvida en dos semanas. Esta lista la mantiene a la vista.
    condicionesPendientes: dominio
      .filter((a) => a.listo)
      .flatMap((a) =>
        a.condicionesEncendido
          .filter((c) => !c.cumplida)
          .map((c) => ({ agente: a.id, condicion: c.condicion, responsable: c.responsable })),
      ),
  };
};
