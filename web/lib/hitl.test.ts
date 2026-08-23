/**
 * La bandeja: el cruce entre un caso de Postgres y el organigrama que vive en git.
 *
 * Los casos son de mentira —Postgres todavia no tiene contrasena— pero el registro y las
 * politicas son los reales. Es la mezcla correcta: lo que se comprueba no es que Postgres
 * devuelva filas, es que la POLITICA vigente enrute y faculte a quien dice.
 *
 * El reloj se pasa siempre por parametro. Una prueba de SLA que dependa de la hora a la que
 * se corre es una prueba que va a fallar sola un martes a las seis.
 */

import { describe, expect, it } from "vitest";

import type { Caso } from "./db/consultas";
import { bandejaDe, restanteLegible } from "./hitl";
import { cargarRegistro, resolverPersona } from "./rbac";

const reg = cargarRegistro();
const persona = (nombre: string) => resolverPersona(nombre, reg);

/** Un viernes a las 10:00 en Ciudad de Mexico, es decir 16:00 UTC: plena jornada habil. */
const VIERNES = Date.parse("2026-06-05T16:00:00Z");

const caso = (parcial: Partial<Caso> & { trace_id: string; responsable: string }): Caso => ({
  tipo: "cotizacion",
  referencia: "CL-01",
  criticidad: "media",
  estado: "esperando_humano",
  abierto_en: new Date(VIERNES),
  actualizado_en: new Date(VIERNES),
  reintentos: 0,
  escalamientos: 0,
  pasos: 3,
  tokens: "0",
  costo_mxn: "0.00",
  ultimo_seq: 4,
  ...parcial,
});

describe("a quien le aparece cada HITL", () => {
  const casos = [
    caso({ trace_id: "TR-A", responsable: "D4-03" }), // equipo T04-03, owner Gabriel
    caso({ trace_id: "TR-B", responsable: "D2-03" }), // equipo T02-02, owner Nay
    caso({ trace_id: "TR-C", responsable: "D3-05" }), // equipo T03-06, owner Elias
  ];

  it("el responsable de un equipo puede aprobar lo suyo", () => {
    const suyos = bandejaDe({
      casos,
      persona: persona("Elias"),
      registro: reg,
      ahora: VIERNES,
      soloLosSuyos: true,
    });
    const c = suyos.find((h) => h.caso.trace_id === "TR-C");
    expect(c?.decision.puede).toBe(true);
  });

  it("un externo no aprueba nada, ni siquiera lo que ve", () => {
    // Regla dura §11.3. Se comprueba explicitamente aunque por construccion un externo no
    // sea owner de nada: un control que solo se cumple por accidente no es un control.
    const bandeja = bandejaDe({ casos, persona: persona("contador"), registro: reg, ahora: VIERNES });
    expect(bandeja.every((h) => !h.decision.puede)).toBe(true);
  });

  it("Direccion puede aprobar cualquiera, porque el comodin esta encendido", () => {
    const bandeja = bandejaDe({ casos, persona: persona("Gabriel"), registro: reg, ahora: VIERNES });
    expect(bandeja.every((h) => h.decision.puede)).toBe(true);
  });

  it("ver no es aprobar: un co-owner ve el caso de su equipo aunque no lo pueda aprobar", () => {
    // Esconderselo convertiria un SLA a punto de vencer en una sorpresa.
    const bandeja = bandejaDe({
      casos,
      persona: persona("Ana"),
      registro: reg,
      ahora: VIERNES,
      soloLosSuyos: true,
    });
    const deD3 = bandeja.find((h) => h.caso.trace_id === "TR-C");
    expect(deD3).toBeDefined();
    expect(deD3?.decision.puede).toBe(false);
  });
});

describe("el umbral decide, y sin umbral no se aprueba", () => {
  const deD403 = [caso({ trace_id: "TR-D", responsable: "D4-03" })];

  it("Ana aprueba un descuento de tarifa de D4-03 porque el gate la nombra", () => {
    // La resolucion de §7.2: `co_owners_con_autoridad` reconoce la autoridad que la tabla de
    // umbrales ya le daba, sin quitarle a Gabriel la responsabilidad del equipo.
    const [h] = bandejaDe({
      casos: deD403,
      persona: persona("Ana"),
      registro: reg,
      umbrales: { "TR-D": "descuento_tarifa" },
      ahora: VIERNES,
    });
    expect(h?.decision.puede).toBe(true);
  });

  it("Ana NO aprueba un umbral que el gate no le atribuye", () => {
    const [h] = bandejaDe({
      casos: deD403,
      persona: persona("Ana"),
      registro: reg,
      umbrales: { "TR-D": "gasto_operativo" },
      ahora: VIERNES,
    });
    expect(h?.decision.puede).toBe(false);
    expect(h?.decision.motivo).toMatch(/no la faculta/i);
  });

  it("un HITL que no declara que umbral disparo no lo aprueba un co-owner", () => {
    // No se aprueba lo que no se sabe que es.
    const [h] = bandejaDe({
      casos: deD403,
      persona: persona("Ana"),
      registro: reg,
      ahora: VIERNES,
    });
    expect(h?.decision.puede).toBe(false);
    expect(h?.decision.motivo).toMatch(/umbral/i);
  });
});

describe("el orden de la bandeja", () => {
  it("lo mas cerca de vencer va primero, y lo vencido antes que todo", () => {
    const hace3dias = VIERNES - 3 * 24 * 60 * 60 * 1000;
    const bandeja = bandejaDe({
      casos: [
        caso({ trace_id: "TR-NUEVO", responsable: "D4-03", criticidad: "baja" }),
        caso({
          trace_id: "TR-VIEJO",
          responsable: "D4-03",
          criticidad: "alta",
          actualizado_en: new Date(hace3dias),
        }),
      ],
      persona: persona("Gabriel"),
      registro: reg,
      ahora: VIERNES,
    });
    expect(bandeja[0]?.caso.trace_id).toBe("TR-VIEJO");
    expect(bandeja[0]?.restanteMs).toBeLessThan(0);
  });

  it("el SLA se cuenta en horas habiles, no en horas de reloj", () => {
    // Un caso que entra a esperar el viernes por la tarde NO vence el sabado. Si esto se
    // rompiera, el portal escalaria en fin de semana casos que nadie podia atender.
    const viernesTarde = Date.parse("2026-06-05T22:00:00Z"); // 16:00 en CDMX
    const [h] = bandejaDe({
      casos: [
        caso({
          trace_id: "TR-V",
          responsable: "D4-03",
          criticidad: "media",
          actualizado_en: new Date(viernesTarde),
        }),
      ],
      persona: persona("Gabriel"),
      registro: reg,
      ahora: viernesTarde,
    });
    const vence = new Date(h!.venceEnMs);
    const dia = vence.getUTCDay();
    expect(dia).not.toBe(0); // domingo
    expect(dia).not.toBe(6); // sabado
  });
});

describe("lo que toca al vencer", () => {
  it("nunca es aprobar, con cero escalamientos o con dos", () => {
    // La regla dura. `Accion` no contiene "aprobar" y `cargarSla()` rechaza una politica que
    // la declare; esto lo comprueba desde el otro lado, sobre casos de la bandeja.
    const hace10dias = VIERNES - 10 * 24 * 60 * 60 * 1000;
    for (const escalamientos of [0, 1, 2]) {
      for (const criticidad of ["alta", "media", "baja"] as const) {
        const [h] = bandejaDe({
          casos: [
            caso({
              trace_id: `TR-${criticidad}-${escalamientos}`,
              responsable: "D4-03",
              criticidad,
              escalamientos,
              actualizado_en: new Date(hace10dias),
            }),
          ],
          persona: persona("Gabriel"),
          registro: reg,
          ahora: VIERNES,
        });
        expect(h?.alVencer).not.toBeNull();
        expect(["escalar", "expirar", "bloquear"]).toContain(h?.alVencer?.accion);
      }
    }
  });
});

describe("sin persona resuelta", () => {
  it("no se concede nada y el motivo lo dice", () => {
    const [h] = bandejaDe({
      casos: [caso({ trace_id: "TR-X", responsable: "D4-03" })],
      persona: null,
      registro: reg,
      ahora: VIERNES,
    });
    expect(h?.decision.puede).toBe(false);
    expect(h?.decision.motivo).toMatch(/no esta vinculada/i);
  });
});

describe("el restante en palabras", () => {
  it("un vencido se dice vencido, no con un numero negativo", () => {
    expect(restanteLegible(-90 * 60_000)).toMatch(/^vencido hace/);
    expect(restanteLegible(-90 * 60_000)).not.toContain("-");
  });

  it("lo que falta se dice en la unidad que se entiende", () => {
    expect(restanteLegible(30 * 60_000)).toBe("30 min");
    expect(restanteLegible(150 * 60_000)).toBe("2 h 30 min");
  });
});
