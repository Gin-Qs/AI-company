/**
 * RBAC: de un nombre a una autoridad, derivado del registro real.
 *
 * Estas pruebas corren contra `registry/` de verdad, no contra un fixture. Es a proposito:
 * lo que se comprueba no es que la funcion sepa sumar, es que la POLITICA vigente concede
 * lo que dice conceder. Si alguien cambia un `owner_humano` en un YAML y con eso deja a una
 * persona sin poder aprobar lo que el gate le atribuye, esto se pone rojo.
 */

import { describe, expect, it } from "vitest";

import {
  agentesDe,
  cargarGate,
  cargarRegistro,
  puedeAprobar,
  resolverPersona,
  responsableDe,
} from "./rbac";

const reg = cargarRegistro();
const persona = (nombre: string) => resolverPersona(nombre, reg);

describe("la politica vigente se lee entera", () => {
  it("nombra a la Direccion, a los operadores y a los externos", () => {
    const gate = cargarGate();
    expect(gate.direccion).toBe("Gabriel");
    expect(Object.values(gate.operadores)).toEqual(
      expect.arrayContaining(["Nay", "Ana", "Elias"]),
    );
    expect(gate.externos).toEqual(expect.arrayContaining(["contador", "abogado"]));
  });

  it("el ruteo es configuracion, no una constante del codigo", () => {
    const { ruteo } = cargarGate();
    expect(ruteo.responsable).toBe("owner_humano_del_equipo");
    expect(ruteo.apruebanAdemas).toBe("co_owners_con_autoridad");
    expect(ruteo.comodinDireccion).toBe(true);
  });
});

describe("a quien le llega cada HITL", () => {
  // Derivado de agente -> teams -> owner_humano. Si un equipo cambia de dueño, cambia aqui.
  it.each([
    ["D1-03", "Gabriel"],
    ["D2-03", "Nay"],
    ["D2-04", "Nay"],
    ["D3-05", "Elias"],
    ["D4-03", "Gabriel"],
  ])("%s responde %s", (agente, esperado) => {
    expect(responsableDe(agente, reg)).toBe(esperado);
  });

  it("un agente que no existe no tiene responsable inventado", () => {
    expect(responsableDe("D9-99", reg)).toBeNull();
  });
});

describe("§7.2 — la contradiccion que este trabajo destapo", () => {
  // El gate dice que Ana aprueba descuentos de hasta 5% y plazos de hasta 45 dias, ambos
  // dominio de D4-03. Pero T04-03 tiene owner_humano: Gabriel, asi que con el ruteo viejo
  // Ana no recibia jamas un HITL de pricing. Las dos cosas no podian ser verdad.
  const ana = persona("Ana");

  it("Ana responde por equipos cuyos agentes todavia no existen: ese era el problema", () => {
    // Ana SI es owner_humano —de T04-04, T07-01 y T07-05— pero los agentes de esos tres
    // equipos (D4-04, D7-01, D7-03) son de fases futuras y no tienen archivo en
    // registry/agents/. Asi que hoy ningun agente EXISTENTE le enruta un HITL.
    expect(ana.equiposResponsable.length).toBeGreaterThan(0);

    const agentesQueLeLlegan = Object.values(reg.agentes).filter(
      (a) => a.tipo === "dominio" && a.equipos.some((e) => ana.equiposResponsable.includes(e)),
    );
    expect(
      agentesQueLeLlegan,
      "si ya existe un agente en un equipo de Ana, actualiza esta prueba",
    ).toEqual([]);
  });

  it("el gate si le atribuye autoridad sobre dos umbrales", () => {
    expect(ana.umbralesConAutoridad).toEqual(
      expect.arrayContaining(["descuento_tarifa", "plazo_de_pago"]),
    );
  });

  it("ahora SI puede aprobar un descuento de tarifa de D4-03", () => {
    const d = puedeAprobar({
      persona: ana,
      agenteId: "D4-03",
      umbral: "descuento_tarifa",
      registro: reg,
    });
    expect(d.puede).toBe(true);
    expect(d.motivo).toContain("descuento_tarifa");
  });

  it("y NO puede aprobar un umbral que el gate no le da", () => {
    const d = puedeAprobar({
      persona: ana,
      agenteId: "D2-04",
      umbral: "pago_proveedor",
      registro: reg,
    });
    expect(d.puede).toBe(false);
    expect(d.motivo).toContain("Nay"); // le dice a quien mandarlo
  });

  it("sin umbral declarado no aprueba nada: no se aprueba lo que no se sabe que es", () => {
    const d = puedeAprobar({ persona: ana, agenteId: "D4-03", registro: reg });
    expect(d.puede).toBe(false);
    expect(d.motivo).toContain("umbral");
  });

  it("Gabriel sigue siendo el responsable de D4-03: la responsabilidad no se diluyo", () => {
    expect(responsableDe("D4-03", reg)).toBe("Gabriel");
  });
});

describe("los owners aprueban lo suyo", () => {
  it("Nay responde por el ciclo de ingreso y aprueba sin necesitar umbral", () => {
    const d = puedeAprobar({ persona: persona("Nay"), agenteId: "D2-04", registro: reg });
    expect(d.puede).toBe(true);
  });

  it("Elias responde por el cierre de viaje", () => {
    expect(puedeAprobar({ persona: persona("Elias"), agenteId: "D3-05", registro: reg }).puede).toBe(
      true,
    );
  });

  it("Elias no aprueba un HITL de finanzas", () => {
    const d = puedeAprobar({ persona: persona("Elias"), agenteId: "D2-04", registro: reg });
    expect(d.puede).toBe(false);
  });
});

describe("el comodin de Direccion", () => {
  it("Gabriel puede aprobar cualquier HITL, tambien los que no responde", () => {
    for (const agente of ["D1-03", "D2-03", "D2-04", "D3-05", "D4-03"]) {
      expect(puedeAprobar({ persona: persona("Gabriel"), agenteId: agente, registro: reg }).puede, agente).toBe(true);
    }
  });

  it("y ve la operacion entera en su bandeja", () => {
    const suyos = agentesDe(persona("Gabriel"), reg);
    expect(suyos).toEqual(expect.arrayContaining(["D1-03", "D2-03", "D2-04", "D3-05", "D4-03"]));
  });
});

describe("regla dura: ningun externo aprueba (§11.3)", () => {
  it.each(["contador", "abogado"])("%s no puede aprobar ningun HITL", (nombre) => {
    const quien = persona(nombre);
    expect(quien.rol).toBe("externo");
    for (const agente of ["D1-03", "D2-03", "D2-04", "D3-05", "D4-03"]) {
      const d = puedeAprobar({ persona: quien, agenteId: agente, umbral: "pago_proveedor", registro: reg });
      expect(d.puede, `${nombre} sobre ${agente}`).toBe(false);
      expect(d.motivo).toContain("externo");
    }
  });

  it("un externo no es owner ni co-owner de nada: la regla se cumple por construccion", () => {
    const quien = persona("contador");
    expect(quien.equiposResponsable).toEqual([]);
    expect(quien.equiposApoyo).toEqual([]);
  });
});

describe("una persona desconocida no entra por descuido", () => {
  it("sin rol y sin equipos no aprueba nada", () => {
    const intruso = persona("Fulano");
    expect(intruso.rol).toBe("sin_rol");
    expect(puedeAprobar({ persona: intruso, agenteId: "D4-03", umbral: "descuento_tarifa", registro: reg }).puede).toBe(
      false,
    );
    expect(agentesDe(intruso, reg)).toEqual([]);
  });
});

describe("cada quien ve lo suyo", () => {
  it("Nay ve sus equipos de finanzas y no el cierre de viaje que responde Elias", () => {
    const suyos = agentesDe(persona("Nay"), reg);
    expect(suyos).toEqual(expect.arrayContaining(["D2-03", "D2-04"]));
    expect(suyos).not.toContain("D3-05");
  });
});
