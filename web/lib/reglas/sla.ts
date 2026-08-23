/**
 * Puerto de `services/runlog/sla.py` — SLA y regla dura de timeout (arquitectura v3 §7.3).
 *
 *     Un HITL vencido escala o expira. Nunca auto-aprueba.
 *
 * ESTE ARCHIVO NO DECLARA NINGUN NUMERO. La jornada, los dias habiles, los festivos y los
 * plazos por criticidad viven en YAML y los lee `lib/registro/politicas.ts`:
 *
 *     registry/policies/calendario-laboral.yaml
 *     registry/policies/authority-gate.yaml -> hitl.sla
 *
 * Aqui solo vive la aritmetica, y existe porque Vercel no ejecuta Python. Dos
 * implementaciones de la misma regla divergen en silencio salvo que algo las ate: lo que
 * las ata es `tests/fixtures/sla-vectores.json`, generado desde el Python real por
 * `scripts/vectores_sla.py` y verificado en cada push por `.github/workflows/validar.yml`.
 * El fixture incluye ademas la configuracion con la que se genero, asi que el test no solo
 * comprueba que los resultados coinciden: comprueba que ambos leen los mismos YAML.
 *
 * SOBRE EL HUSO. El registro guarda `ts` en UTC y Vercel ejecuta en UTC, pero la jornada
 * es hora local de la empresa. Por eso aqui NO se usa `getHours()` ni ningun getter local
 * de `Date` — dependen del huso de la maquina, que en tu portatil y en Vercel no son el
 * mismo. Se trabaja en milisegundos y se desplaza el instante a "hora de pared local"
 * sumando el offset, leyendo despues con getters UTC, deterministas en todas partes.
 */

import {
  cargarCalendario,
  cargarSla,
  NuncaAutoAprueba,
  type Accion,
  type Calendario,
  type ReglaSLA,
} from "../registro/politicas";

export { NuncaAutoAprueba };
export type { Accion, Calendario, ReglaSLA };

const MS_DIA = 24 * 60 * 60 * 1000;
const MS_HORA = 60 * 60 * 1000;

export class CriticidadDesconocida extends Error {}

// La politica se lee una vez por proceso. En Vercel cada invocacion arranca en frio, asi
// que un cambio de YAML entra con el siguiente despliegue — que es exactamente cuando debe
// entrar: la politica cambia por PR, no en caliente.
let calendarioPorDefecto: Calendario | null = null;
let slaPorDefecto: Record<string, ReglaSLA> | null = null;

export const calendario = (): Calendario =>
  (calendarioPorDefecto ??= cargarCalendario());

export const reglas = (): Record<string, ReglaSLA> => (slaPorDefecto ??= cargarSla());

/** Solo para pruebas: obliga a releer los YAML en la siguiente llamada. */
export const olvidarPoliticas = (): void => {
  calendarioPorDefecto = null;
  slaPorDefecto = null;
};

// --- aritmetica del calendario ---------------------------------------------
// Estas funciones trabajan en "milisegundos locales": el instante UTC ya desplazado, de
// modo que leerlo con getters UTC devuelve la hora de pared de oficina.

const aLocal = (utcMs: number, cal: Calendario): number => utcMs + cal.offsetMs;
const aUtc = (localMs: number, cal: Calendario): number => localMs - cal.offsetMs;

/** Milisegundos transcurridos del dia. El doble modulo cubre fechas anteriores a 1970. */
const msDelDia = (localMs: number): number => ((localMs % MS_DIA) + MS_DIA) % MS_DIA;

const inicioDelDia = (localMs: number): number => localMs - msDelDia(localMs);

/** "AAAA-MM-DD" de la fecha local, para comparar contra la lista de festivos. */
const fechaLocal = (localMs: number): string =>
  new Date(localMs).toISOString().slice(0, 10);

/**
 * Dia habil declarado y que no sea festivo. Un festivo cuenta igual que un sabado.
 *
 * `getUTCDay()` cuenta 0=domingo; el YAML y Python cuentan 0=lunes. La conversion esta
 * aqui, en un solo lugar, y no repartida por el archivo.
 */
const esDiaHabil = (localMs: number, cal: Calendario): boolean => {
  const diaPython = (new Date(localMs).getUTCDay() + 6) % 7;
  return cal.diasHabiles.has(diaPython) && !cal.festivos.has(fechaLocal(localMs));
};

export const esHabil = (utcMs: number, cal: Calendario = calendario()): boolean => {
  const local = aLocal(utcMs, cal);
  const t = msDelDia(local);
  return esDiaHabil(local, cal) && t >= cal.aperturaMs && t < cal.cierreMs;
};

/** El siguiente instante en que la oficina esta abierta, o el mismo si ya lo esta. */
const siguienteApertura = (localMs: number, cal: Calendario): number => {
  let c = localMs;
  const t = msDelDia(c);
  if (t >= cal.cierreMs) {
    c = inicioDelDia(c) + MS_DIA + cal.aperturaMs;
  } else if (t < cal.aperturaMs) {
    c = inicioDelDia(c) + cal.aperturaMs;
  }
  // Un instante dentro de la jornada pero en sabado —o en festivo— no entra en ninguna
  // rama de arriba: lo mueve este bucle, igual que en el Python.
  while (!esDiaHabil(c, cal)) {
    c = inicioDelDia(c) + MS_DIA + cal.aperturaMs;
  }
  return c;
};

/** Avanza `horas` de reloj laboral desde un momento cualquiera. Entra y sale en UTC. */
export const sumarHorasHabiles = (
  utcMs: number,
  horas: number,
  cal: Calendario = calendario(),
): number => {
  if (horas < 0) throw new RangeError("no se puede sumar un SLA negativo");
  let momento = siguienteApertura(aLocal(utcMs, cal), cal);
  let restante = horas * MS_HORA;

  while (restante > 0) {
    const finDelDia = inicioDelDia(momento) + cal.cierreMs;
    const disponible = finDelDia - momento;
    if (restante <= disponible) return aUtc(momento + restante, cal);
    restante -= disponible;
    momento = siguienteApertura(finDelDia, cal);
  }
  return aUtc(momento, cal);
};

export const sumarDiasHabiles = (
  utcMs: number,
  dias: number,
  cal: Calendario = calendario(),
): number => sumarHorasHabiles(utcMs, dias * cal.horasPorDia, cal);

/** Cuantas horas de reloj laboral concede la politica a esta criticidad. */
const horasDe = (regla: ReglaSLA, cal: Calendario): number =>
  regla.horasHabiles ?? (regla.diasHabiles ?? 0) * cal.horasPorDia;

export const vencimiento = (
  utcMs: number,
  criticidad: string,
  cal: Calendario = calendario(),
  sla: Record<string, ReglaSLA> = reglas(),
): number => {
  const regla = sla[criticidad];
  if (!regla) throw new CriticidadDesconocida(`criticidad desconocida: ${criticidad}`);
  return sumarHorasHabiles(utcMs, horasDe(regla, cal), cal);
};

// --- la decision al vencer --------------------------------------------------

export interface Vencimiento {
  traceId: string;
  criticidad: string;
  venceEn: number;
  accion: Accion;
  escalamientosPrevios: number;
  motivo: string;
}

const MOTIVOS = {
  escalar: "vencio el SLA: escala al siguiente nivel",
  expirarPrimera: "vencio el SLA de criticidad baja: expira y se cierra como no_atendido",
  expirarTrasEscalar: "vencio y ya se habia escalado: expira y se cierra como no_atendido",
  bloquear:
    "vencio despues de escalar: el caso queda bloqueado hasta que una persona lo resuelva",
} as const;

/**
 * Que hacer con un HITL que espera. `null` si todavia no vence.
 *
 * La salida nunca es "aprobar" — el tipo `Accion` no la contiene y `cargarSla()` rechaza
 * una politica que la declare. Con la politica vigente: alta escala y deja el caso
 * bloqueado; media escala una vez y luego expira; baja expira.
 */
export const resolverVencimiento = (args: {
  traceId: string;
  criticidad: string;
  esperaDesde: number;
  ahora: number;
  escalamientos?: number;
  calendario?: Calendario;
  sla?: Record<string, ReglaSLA>;
}): Vencimiento | null => {
  const cal = args.calendario ?? calendario();
  const sla = args.sla ?? reglas();
  const escalamientos = args.escalamientos ?? 0;

  const regla = sla[args.criticidad];
  if (!regla) throw new CriticidadDesconocida(`criticidad desconocida: ${args.criticidad}`);

  const limite = vencimiento(args.esperaDesde, args.criticidad, cal, sla);
  if (args.ahora < limite) return null;

  const accion: Accion = escalamientos === 0 ? regla.alVencer : regla.luego;

  let motivo: string;
  if (accion === "escalar") motivo = MOTIVOS.escalar;
  else if (accion === "bloquear") motivo = MOTIVOS.bloquear;
  else motivo = escalamientos ? MOTIVOS.expirarTrasEscalar : MOTIVOS.expirarPrimera;

  return {
    traceId: args.traceId,
    criticidad: args.criticidad,
    venceEn: limite,
    accion,
    escalamientosPrevios: escalamientos,
    motivo,
  };
};

/**
 * El calendario del YAML con los festivos declarados en Postgres anadidos.
 *
 * Existe porque los festivos dejaron de vivir en `calendario-laboral.yaml` (ver
 * `scripts/sql/0003`): el huso, la jornada y los dias habiles siguen siendo politica en git,
 * pero la lista de feriados es un catalogo de la empresa que se captura desde el portal.
 *
 * Se pasa por parametro y no se lee aqui a proposito: leerlos es asincrono —una consulta— y
 * estas funciones son sincronas. Quien pinta la pagina los trae; quien los trae tambien se
 * asegura de que **no poder leerlos** sea un error visible y no una lista vacia, porque una
 * lista vacia es un calendario que afirma que se trabaja todos los dias y acorta el SLA sin
 * decirlo.
 */
export const conFestivos = (
  base: Calendario,
  declarados: Iterable<string>,
): Calendario => {
  // Union, no reemplazo: lo que quede escrito en el YAML sigue contando. Que la fuente se
  // haya movido no invalida lo que alguien ya habia declarado ahi.
  const fechas = new Set(base.festivos);
  for (const f of declarados) fechas.add(String(f).slice(0, 10));
  return { ...base, festivos: fechas };
};
