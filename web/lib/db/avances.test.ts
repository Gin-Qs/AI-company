/**
 * Los avances de caso: la pieza que faltaba para que la bandeja se llene.
 *
 * `resolverHitl` sacaba casos de `esperando_humano` y nada los metia, asi que un encargo
 * convocado se quedaba en `recibido` para siempre. Estas pruebas fijan la tabla de avances
 * y —sobre todo— lo que NO se puede hacer desde aqui.
 *
 * No tocan la base: lo que se comprueba es la tabla de transiciones y su acuerdo con la
 * maquina de estados de `caso.py`, que es donde vive el riesgo. Un avance que el portal
 * permitiera y el registro no, o al reves, seria dos maquinas de estados.
 */

import { describe, expect, it } from "vitest";

import { AVANCES, DESTINO, TRANSICIONES, type Avance } from "./escrituras";

const avances = Object.entries(AVANCES) as Array<[Avance, (typeof AVANCES)[Avance]]>;

describe("la tabla de avances no contradice la maquina de estados", () => {
  it.each(avances)("%s sale de estados que de verdad llegan a su destino", (nombre, regla) => {
    // Si la tabla permitiera un salto que `caso.py` no admite, el portal ofreceria un boton
    // que siempre falla — o peor, escribiria un estado que el `check` de la columna rechaza.
    for (const desde of regla.desde) {
      expect(TRANSICIONES[desde], `${desde} no existe en la maquina`).toBeDefined();
      expect(
        TRANSICIONES[desde]?.includes(regla.a),
        `${nombre}: ${desde} -> ${regla.a} no lo permite caso.py`,
      ).toBe(true);
    }
  });

  it("todo destino es un estado declarado", () => {
    for (const [, regla] of avances) {
      expect(Object.keys(TRANSICIONES)).toContain(regla.a);
    }
  });
});

describe("lo que el portal NO puede hacer desde la pantalla del caso", () => {
  it("ningun avance entrega un caso", () => {
    // Un caso se entrega desde la BANDEJA, con la firma de quien tiene autoridad. Si se
    // pudiera cerrar moviendolo, el Gate seria opcional y la bandeja decorativa.
    for (const [nombre, regla] of avances) {
      expect(regla.a, `${nombre} entrega el caso sin pasar por el Gate`).not.toBe("entregado");
    }
  });

  it("ningun avance expira un caso", () => {
    // Expirar es lo que le pasa a un caso que NADIE miro. Que una persona pueda expirarlo a
    // mano borraria la diferencia entre un descuido y una decision.
    for (const [nombre, regla] of avances) {
      expect(regla.a, `${nombre} expira el caso a mano`).not.toBe("expirado");
    }
  });

  it("de esperando_humano solo se puede salir bloqueando", () => {
    // La bandeja es la unica puerta de salida hacia entregado. Desde el caso, lo unico
    // legitimo es sacarlo porque falta algo para poder decidir.
    const desdeBandeja = avances.filter(([, r]) => (r.desde as readonly string[]).includes("esperando_humano"));
    expect(desdeBandeja.map(([n]) => n)).toEqual(["bloquear"]);
  });

  it("los destinos de la bandeja y los de los avances no se solapan", () => {
    // `DESTINO` (aprobar/rechazar) y `AVANCES` tienen que ser dos conjuntos de acciones
    // distintos. Si un avance produjera el mismo estado que una aprobacion, habria dos
    // caminos a "entregado" con reglas de autoridad distintas.
    const deLaBandeja = new Set(Object.values(DESTINO));
    const deLosAvances = avances.map(([, r]) => r.a);
    expect(deLosAvances.filter((a) => deLaBandeja.has(a as never))).toEqual(["bloqueado"]);
    // `bloqueado` si es comun a proposito: rechazar bloquea, y bloquear tambien.
  });
});

describe("el ciclo se puede recorrer entero", () => {
  it("de recibido a la bandeja hay camino con los avances disponibles", () => {
    // La prueba de que el hueco quedo cerrado: un encargo recien convocado tiene que poder
    // llegar a `esperando_humano` usando SOLO lo que el portal ofrece.
    let estado = "recibido";
    const camino = [estado];
    for (const paso of ["empezar", "mandar_a_firma"] as Avance[]) {
      const regla = AVANCES[paso];
      expect((regla.desde as readonly string[]), `${paso} desde ${estado}`).toContain(estado);
      estado = regla.a;
      camino.push(estado);
    }
    expect(camino).toEqual(["recibido", "en_proceso", "esperando_humano"]);
  });

  it("y de la bandeja se sale entregando, que ya es de resolverHitl", () => {
    expect(TRANSICIONES["esperando_humano"]).toContain(DESTINO.aprobar);
  });

  it("un caso bloqueado puede volver a la operacion", () => {
    // Bloquear no es un callejon sin salida: lo contrario convertiria cada falta de contexto
    // en un caso perdido.
    expect((AVANCES.desbloquear.desde as readonly string[])).toContain("bloqueado");
    expect(AVANCES.desbloquear.a).toBe("en_proceso");
  });
});

describe("cada avance dice que hizo", () => {
  it("todos tienen verbo, para que el motivo del evento se lea solo", () => {
    // El motivo se guarda como «<verbo>: <lo que escribio la persona>». Ademas de leerse
    // mejor, impide que un motivo humano empiece con "escalamiento" y descuadre el conteo
    // al replegar el registro.
    for (const [nombre, regla] of avances) {
      expect(regla.verbo, nombre).toBeTruthy();
      expect(regla.verbo.startsWith("escalamiento"), nombre).toBe(false);
    }
  });
});
