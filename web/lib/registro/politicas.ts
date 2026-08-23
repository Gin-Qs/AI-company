/**
 * Lectura de las politicas del registro. Solo lectura, siempre.
 *
 * El portal NO escribe en `registry/`. Esa carpeta cambia por PR, se valida con las
 * reglas de `scripts/validate_registry.py` y se audita en el historial de git. Un umbral
 * que se puede cambiar desde una pantalla es un umbral sin auditoria.
 *
 * Estas funciones leen exactamente los mismos archivos que el Python:
 *
 *     registry/policies/calendario-laboral.yaml   huso, jornada, dias habiles, festivos
 *     registry/policies/authority-gate.yaml       hitl.sla
 *
 * En Vercel el directorio raiz del proyecto es `web/`, asi que estos archivos quedan
 * fuera del bundle salvo que `next.config.ts` los incluya con `outputFileTracingIncludes`.
 * Sin eso esto compila en local y devuelve "archivo no encontrado" en produccion.
 */

import { readFileSync } from "node:fs";

import { parse } from "yaml";

import { desdeRaiz } from "../rutas";

export const rutaCalendario = (): string =>
  desdeRaiz("registry", "policies", "calendario-laboral.yaml");
export const rutaGate = (): string =>
  desdeRaiz("registry", "policies", "authority-gate.yaml");

/** Las unicas consecuencias posibles al vencer un HITL (§7.3). "aprobar" no esta. */
export const ACCIONES = ["escalar", "expirar", "bloquear"] as const;
export type Accion = (typeof ACCIONES)[number];

/**
 * Se declaro una consecuencia que aprueba. Es la unica salida prohibida.
 *
 * Igual que en el Python, se levanta al CARGAR la politica y no al aplicarla: un
 * `al_vencer: aprobar` tiene que reventar el arranque, no descubrirse el dia que un HITL
 * vence sin que nadie lo mire.
 */
export class NuncaAutoAprueba extends Error {}

export class PoliticaInvalida extends Error {}

export interface Calendario {
  /** Desplazamiento del huso en milisegundos. Negativo al oeste de Greenwich. */
  offsetMs: number;
  aperturaMs: number;
  cierreMs: number;
  /** 0 = lunes … 6 = domingo, la convencion de `datetime.weekday()` de Python. */
  diasHabiles: ReadonlySet<number>;
  /** Fechas "AAAA-MM-DD" que no cuentan para el reloj, igual que un sabado. */
  festivos: ReadonlySet<string>;
  horasPorDia: number;
  calibrado: string;
  version: string;
}

export interface ReglaSLA {
  criticidad: string;
  alVencer: Accion;
  luego: Accion;
  horasHabiles: number | null;
  diasHabiles: number | null;
  resumen: string;
}

const MS_HORA = 60 * 60 * 1000;

/** "09:00" o "09:30:00" -> milisegundos desde la medianoche. */
const aMsDelDia = (texto: string, campo: string): number => {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(String(texto).trim());
  if (!m) throw new PoliticaInvalida(`${campo} no es una hora valida: ${texto}`);
  const [h, min, seg] = [Number(m[1]), Number(m[2]), Number(m[3] ?? 0)];
  if (h > 23 || min > 59 || seg > 59) {
    throw new PoliticaInvalida(`${campo} no es una hora valida: ${texto}`);
  }
  return ((h * 60 + min) * 60 + seg) * 1000;
};

const leer = (ruta: string): unknown => parse(readFileSync(ruta, "utf-8"));

export const cargarCalendario = (ruta: string = rutaCalendario()): Calendario => {
  const datos = (leer(ruta) ?? {}) as Record<string, any>;
  const huso = datos.huso ?? {};
  const jornada = datos.jornada ?? {};
  const festivos = datos.festivos ?? {};

  const aperturaMs = aMsDelDia(jornada.apertura ?? "09:00", "apertura");
  const cierreMs = aMsDelDia(jornada.cierre ?? "18:00", "cierre");
  if (aperturaMs >= cierreMs) {
    throw new PoliticaInvalida(
      `la jornada abre a las ${jornada.apertura} y cierra a las ${jornada.cierre}: nunca avanzaria el reloj`,
    );
  }

  // `??` y no `||`: una lista vacia es un valor declarado, no un valor ausente. "No lo
  // declare" y "declare que no hay ninguno" no son lo mismo, y confundirlos convertiria
  // `dias_habiles: []` en lunes-a-viernes sin avisar.
  const declarados: unknown = jornada.dias_habiles ?? [0, 1, 2, 3, 4];
  if (!Array.isArray(declarados) || declarados.length === 0) {
    throw new PoliticaInvalida("no hay ni un dia habil: ningun SLA podria vencer");
  }
  const diasHabiles = new Set(declarados.map(Number));
  for (const d of diasHabiles) {
    if (!Number.isInteger(d) || d < 0 || d > 6) {
      throw new PoliticaInvalida(`dia habil fuera de rango 0-6: ${d}`);
    }
  }

  // El parser de YAML devuelve `Date` para una fecha sin comillas y `string` con ellas.
  // Se normaliza a "AAAA-MM-DD" para poder comparar sin depender del huso del proceso.
  const fechas = new Set<string>(
    ((festivos.fechas ?? []) as unknown[]).map((f) =>
      f instanceof Date ? f.toISOString().slice(0, 10) : String(f).trim().slice(0, 10),
    ),
  );

  return {
    offsetMs: Number(huso.offset_horas ?? -6) * MS_HORA,
    aperturaMs,
    cierreMs,
    diasHabiles,
    festivos: fechas,
    horasPorDia: (cierreMs - aperturaMs) / MS_HORA,
    calibrado: String(datos.calibrado ?? "parcial"),
    version: String(datos.version ?? "v1"),
  };
};

export const cargarSla = (ruta: string = rutaGate()): Record<string, ReglaSLA> => {
  const datos = (leer(ruta) ?? {}) as Record<string, any>;
  const crudo = datos.hitl?.sla;
  if (!crudo || Object.keys(crudo).length === 0) {
    throw new PoliticaInvalida("authority-gate.yaml no declara hitl.sla");
  }

  const reglas: Record<string, ReglaSLA> = {};
  for (const [criticidad, regla] of Object.entries(crudo as Record<string, any>)) {
    const alVencer = String(regla.al_vencer ?? "");
    const luego = String(regla.luego ?? alVencer);

    for (const accion of [alVencer, luego]) {
      if (!(ACCIONES as readonly string[]).includes(accion)) {
        throw new NuncaAutoAprueba(
          `hitl.sla.${criticidad} declara "${accion}", que no es una consecuencia permitida. ` +
            `Un HITL vencido escala o expira; nunca auto-aprueba (§7.3). ` +
            `Validas: ${ACCIONES.join(", ")}`,
        );
      }
    }

    if (regla.horas_habiles == null && regla.dias_habiles == null) {
      throw new PoliticaInvalida(
        `hitl.sla.${criticidad} no declara plazo: falta horas_habiles o dias_habiles`,
      );
    }

    reglas[criticidad] = {
      criticidad,
      alVencer: alVencer as Accion,
      luego: luego as Accion,
      horasHabiles: regla.horas_habiles ?? null,
      diasHabiles: regla.dias_habiles ?? null,
      resumen: String(regla.resumen ?? ""),
    };
  }
  return reglas;
};
