/**
 * El contrato entre las dos implementaciones del calendario laboral.
 *
 * Los vectores NO se escriben a mano aqui: los genera `scripts/vectores_sla.py` desde
 * `services/runlog/sla.py`, que es la fuente de verdad del comportamiento. Escribirlos a
 * mano convertiria este archivo en una tercera opinion sobre lo mismo.
 *
 * Se prueba a proposito con el huso de la maquina puesto en algo que NO es el de la
 * empresa (ver `vitest.config.ts`, TZ=UTC): si el puerto usara getters locales de `Date`
 * en vez de aritmetica de milisegundos, aqui es donde se veria.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { cargarCalendario, cargarSla, NuncaAutoAprueba } from "../registro/politicas";
import {
  calendario,
  reglas,
  resolverVencimiento,
  sumarHorasHabiles,
  vencimiento,
  type Calendario,
} from "./sla";

interface Vectores {
  calendario: {
    offset_horas: number;
    apertura: string;
    cierre: string;
    dias_habiles: number[];
    festivos: string[];
    horas_por_dia: number;
    calibrado: string;
  };
  sla: Record<
    string,
    {
      horas_habiles: number | null;
      dias_habiles: number | null;
      al_vencer: string;
      luego: string;
    }
  >;
  vencimientos: Array<{
    espera_desde_utc: string;
    criticidad: string;
    vence_en_utc: string;
    vence_en_local: string;
    dia_local: string;
    por_que: string;
  }>;
  decisiones_al_vencer: Array<{
    espera_desde_utc: string;
    criticidad: string;
    escalamientos_previos: number;
    se_pregunta_en_utc: string;
    accion: string | null;
    por_que: string;
  }>;
}

const vectores: Vectores = JSON.parse(
  readFileSync(
    new URL("../../../tests/fixtures/sla-vectores.json", import.meta.url),
    "utf-8",
  ),
);

const ms = (iso: string): number => Date.parse(iso);

// ---------------------------------------------------------------------------

describe("las dos implementaciones leen la misma politica", () => {
  // Reproducir los resultados correctos con la configuracion equivocada seria acertar por
  // suerte, y la suerte se acaba el dia que alguien edita el YAML.
  it("el calendario que lee TypeScript es el que uso el Python", () => {
    const cal = cargarCalendario();
    const esperado = vectores.calendario;

    expect(cal.offsetMs / 3_600_000).toBe(esperado.offset_horas);
    expect(cal.horasPorDia).toBe(esperado.horas_por_dia);
    expect([...cal.diasHabiles].sort()).toEqual([...esperado.dias_habiles].sort());
    expect([...cal.festivos].sort()).toEqual([...esperado.festivos].sort());
    expect(cal.calibrado).toBe(esperado.calibrado);
  });

  it("los plazos que lee TypeScript son los que uso el Python", () => {
    const sla = cargarSla();
    for (const [criticidad, esperada] of Object.entries(vectores.sla)) {
      const regla = sla[criticidad];
      expect(regla, `falta la criticidad ${criticidad}`).toBeDefined();
      expect(regla!.horasHabiles).toBe(esperada.horas_habiles);
      expect(regla!.diasHabiles).toBe(esperada.dias_habiles);
      expect(regla!.alVencer).toBe(esperada.al_vencer);
      expect(regla!.luego).toBe(esperada.luego);
    }
  });
});

describe("vencimiento: cuando vence un HITL", () => {
  it.each(vectores.vencimientos)(
    "$criticidad desde $espera_desde_utc -> $vence_en_local ($dia_local): $por_que",
    (v) => {
      expect(new Date(vencimiento(ms(v.espera_desde_utc), v.criticidad)).toISOString()).toBe(
        new Date(ms(v.vence_en_utc)).toISOString(),
      );
    },
  );

  it("cubre el arranque en sabado, antes de abrir y despues de cerrar", () => {
    // Si alguien recorta los vectores, el contrato se vacia sin que ningun test truene.
    expect(vectores.vencimientos.length).toBeGreaterThanOrEqual(10);
  });
});

describe("resolverVencimiento: que se hace al vencer", () => {
  it.each(vectores.decisiones_al_vencer)(
    "$criticidad con $escalamientos_previos escalamientos -> $accion: $por_que",
    (d) => {
      const fallo = resolverVencimiento({
        traceId: "TR-VECTOR",
        criticidad: d.criticidad,
        esperaDesde: ms(d.espera_desde_utc),
        ahora: ms(d.se_pregunta_en_utc),
        escalamientos: d.escalamientos_previos,
      });
      expect(fallo?.accion ?? null).toBe(d.accion);
    },
  );

  it("ninguna consecuencia de la politica vigente aprueba (regla dura §7.3)", () => {
    for (const [criticidad, regla] of Object.entries(reglas())) {
      expect(["escalar", "expirar", "bloquear"], criticidad).toContain(regla.alVencer);
      expect(["escalar", "expirar", "bloquear"], criticidad).toContain(regla.luego);
    }
  });
});

// ---------------------------------------------------------------------------

describe("la configuracion configura de verdad", () => {
  // Mismo criterio que tests/unit/test_calendario.py del lado Python: "es configurable"
  // es facil de afirmar y dificil de comprobar. Cada prueba cambia un valor y exige que
  // el comportamiento cambie con el.
  const base = (): Calendario => cargarCalendario();

  const con = (cambios: Partial<Calendario>): Calendario => ({ ...base(), ...cambios });

  it("un festivo no cuenta para el reloj", () => {
    const martes = Date.parse("2026-09-15T22:00:00Z"); // 16:00 local, quedan 2h
    const conFestivo = con({ festivos: new Set(["2026-09-16"]) });

    // El miercoles 16 es feriado: las 2h restantes caen el jueves 17 por la mañana.
    expect(new Date(sumarHorasHabiles(martes, 4, conFestivo)).toISOString()).toBe(
      "2026-09-17T17:00:00.000Z", // 11:00 local
    );
  });

  it("sin festivos el mismo caso vence un dia antes", () => {
    const martes = Date.parse("2026-09-15T22:00:00Z");
    expect(new Date(sumarHorasHabiles(martes, 4, base())).toISOString()).toBe(
      "2026-09-16T17:00:00.000Z",
    );
  });

  it("una jornada mas larga hace que el mismo plazo venza antes", () => {
    const lunes = Date.parse("2026-06-01T22:00:00Z"); // 16:00 local
    const larga = con({
      aperturaMs: 8 * 3_600_000,
      cierreMs: 20 * 3_600_000,
      horasPorDia: 12,
    });

    expect(sumarHorasHabiles(lunes, 6, larga)).toBeLessThan(
      sumarHorasHabiles(lunes, 6, base()),
    );
  });

  it("la jornada declarada es la que usa el reloj, no una constante", () => {
    expect(base().horasPorDia).toBe(vectores.calendario.horas_por_dia);
  });
});

describe("la regla dura se impone al cargar la politica", () => {
  it("una politica que auto-aprueba no se carga", () => {
    // El mismo criterio que el Python: un `al_vencer: aprobar` tiene que reventar al
    // cargar, no descubrirse el dia que un pago se aprueba solo porque nadie lo miro.
    const ruta = new URL("./__fixtures__/gate-que-aprueba.yaml", import.meta.url);
    expect(() => cargarSla(ruta.pathname.replace(/^\/([A-Za-z]:)/, "$1"))).toThrow(
      NuncaAutoAprueba,
    );
  });
});

describe("el calendario declara si esta calibrado", () => {
  it("los festivos siguen sin cargar, y el portal tiene que poder decirlo", () => {
    const cal = calendario();
    expect(cal.calibrado).toBe("parcial");
    expect(cal.festivos.size, "si ya cargaste los festivos, actualiza esta prueba").toBe(0);
  });
});
