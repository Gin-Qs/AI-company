/**
 * El lector del registro, contra `registry/` de verdad.
 *
 * Ninguna prueba de aqui fija un total en duro. Dar de alta un agente no puede romper la
 * suite: el organigrama tiene que poder crecer sin pedir permiso. Lo que se comprueba son
 * relaciones —quien tiene identidad se dibuja, quien esta `listo` declara que le falta—
 * porque la relacion es la invariante y el numero es una consecuencia.
 */

import { describe, expect, it } from "vitest";

import { cargarAgentes, cargarEquipos, cargarIdentidades, panorama, ESTADOS } from "./index";

const agentes = cargarAgentes();
const equipos = cargarEquipos();

describe("carga", () => {
  it("lee agentes de dominio y consultores, y los distingue", () => {
    const dominio = Object.values(agentes).filter((a) => a.tipo === "dominio");
    const consultores = Object.values(agentes).filter((a) => a.tipo === "consultor");
    expect(dominio.length).toBeGreaterThan(0);
    expect(consultores.length).toBeGreaterThan(0);
    expect(consultores.every((c) => c.id.startsWith("C-"))).toBe(true);
  });

  it("todo estado declarado es uno de los cuatro del ciclo de vida", () => {
    for (const a of Object.values(agentes)) {
      if (a.tipo !== "dominio") continue;
      expect(ESTADOS, `${a.id} declara un estado desconocido`).toContain(a.estado);
    }
  });

  it("lee los equipos con su owner humano y sus co-owners", () => {
    expect(Object.keys(equipos).length).toBeGreaterThan(0);
    for (const e of Object.values(equipos)) {
      expect(e.ownerHumano, `${e.id} sin owner_humano`).toBeTruthy();
    }
  });
});

describe("reglas duras que el lector tiene que reflejar", () => {
  it("ningun consultor declara un ACT-*", () => {
    // §5-bis.1: si un consultor necesitara un ACT-*, el trabajo no es de consultoria.
    for (const c of Object.values(agentes).filter((a) => a.tipo === "consultor")) {
      expect(c.acciones, `${c.id} declara ACT-*`).toEqual([]);
    }
  });

  it("todo agente con ACT-* declara al menos un CTL-* que lo controle", () => {
    for (const a of Object.values(agentes)) {
      if (a.acciones.length === 0) continue;
      expect(a.controles.length, `${a.id} tiene ACT-* sin CTL-*`).toBeGreaterThan(0);
    }
  });

  it("un agente retirado no conserva acciones", () => {
    for (const a of Object.values(agentes).filter((x) => x.retirado)) {
      expect(a.acciones, `${a.id} esta retirado y sigue ejecutando`).toEqual([]);
    }
  });
});

describe("lo que la vista de agentes necesita", () => {
  it("todo agente con identidad trae escritorio, zona y sprite", () => {
    const zonas = cargarIdentidades().zonas;
    for (const a of Object.values(agentes)) {
      if (!a.identidad) continue;
      expect(a.identidad.sprite, `${a.id} sin sprite`).toBeTruthy();
      expect(Object.keys(zonas), `${a.id} en una zona inexistente`).toContain(a.identidad.zona);
    }
  });

  it("todo agente `listo` dice que le falta y quien lo cierra", () => {
    // Un agente completo y sin encender es legitimo y peligroso: el trabajo esta hecho,
    // nadie lo usa y la razon se olvida en dos semanas.
    for (const a of Object.values(agentes).filter((x) => x.listo)) {
      expect(a.condicionesEncendido.length, `${a.id} listo sin condiciones`).toBeGreaterThan(0);
      for (const c of a.condicionesEncendido) {
        expect(c.condicion, `${a.id} con una condicion vacia`).toBeTruthy();
        expect(c.responsable, `${a.id}: "${c.condicion}" sin responsable`).toBeTruthy();
      }
    }
  });
});

describe("panorama: lo que ve la pantalla de resumen", () => {
  const p = panorama(agentes);

  it("las cifras cuadran entre si", () => {
    const dominio = Object.values(agentes).filter((a) => a.tipo === "dominio");
    expect(p.total).toBe(dominio.length);
    expect(p.disponibles + p.listos + p.planeados + p.retirados).toBe(p.total);
  });

  it("lista las condiciones pendientes con dueño, no solo el conteo", () => {
    for (const c of p.condicionesPendientes) {
      expect(c.responsable, `${c.agente}: "${c.condicion}" sin responsable`).toBeTruthy();
    }
  });

  it("el portal es la condicion que bloquea a los agentes del MVP", () => {
    // La razon de ser de todo esto (docs/portal.md §1). Si algun dia esta prueba falla
    // porque ya nadie espera la bandeja, es que el portal se termino.
    const esperandoBandeja = p.condicionesPendientes.filter((c) =>
      c.condicion.includes("Bandeja única de HITL"),
    );
    expect(esperandoBandeja.length).toBeGreaterThan(0);
  });
});
