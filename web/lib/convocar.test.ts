/**
 * El puerto de `convocar()`, contrastado contra el Python real.
 *
 * `tests/fixtures/convocatoria-vectores.json` lo genera `scripts/vectores_convocatoria.py`
 * llamando a `agents/runtime.py:convocar()` agente por agente. Aqui se exige el mismo
 * veredicto. Si alguien relaja una regla en un lado, esto se pone rojo — que es lo unico que
 * impide que el portal deje convocar a quien el CLI habria rechazado.
 *
 * Los vectores se generan con la oficina abierta y sin base de datos, para que cada uno
 * aisle la regla del agente. La pausa gana sobre todo lo demas y taparia el resto de los
 * veredictos, asi que se prueba aparte, mas abajo.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { convocablesPor, puedeConvocar, type Borrador } from "./convocar";
import { cargarRegistro, resolverPersona } from "./rbac";
import { desdeRaiz } from "./rutas";

interface Vector {
  agente: string;
  convocado_por: string;
  encargo_completo: boolean;
  campo_vacio?: string;
  puede: boolean;
  motivo?: string;
}

const fixture = JSON.parse(
  readFileSync(join(desdeRaiz("tests", "fixtures"), "convocatoria-vectores.json"), "utf-8"),
) as { borrador_completo: Record<string, string>; vectores: Vector[] };

const reg = cargarRegistro();
const ABIERTA = { activa: false };

const borradorDe = (v: Vector): Borrador => {
  const c = fixture.borrador_completo;
  const campos: Record<string, string> = {
    titulo: c.titulo!,
    descripcion: c.descripcion!,
    entregable_esperado: c.entregable_esperado!,
  };
  if (v.campo_vacio) campos[v.campo_vacio] = "   ";
  return {
    agenteId: v.agente,
    titulo: campos.titulo!,
    descripcion: campos.descripcion!,
    entregableEsperado: campos.entregable_esperado!,
    hitl: false,
  };
};

describe("el contrato con agents/runtime.py", () => {
  it("hay vectores que cubrir", () => {
    // Un fixture vacio haria que el `it.each` de abajo no corriera NADA y la suite se viera
    // verde sin haber comprobado el puerto.
    expect(fixture.vectores.length).toBeGreaterThan(20);
  });

  it.each(fixture.vectores)(
    "$agente convocado por $convocado_por (completo: $encargo_completo) -> $motivo",
    (v: Vector) => {
      const veredicto = puedeConvocar({
        borrador: borradorDe(v),
        // La persona se resuelve del registro real; "Nadie" sale `sin_rol`, que es
        // justamente el caso que prueba `invocable_por`.
        persona: resolverPersona(v.convocado_por, reg),
        registro: reg,
        pausa: ABIERTA,
      });

      expect(veredicto.puede).toBe(v.puede);
      if (!v.puede && !veredicto.puede) {
        expect(veredicto.motivo).toBe(v.motivo);
      }
    },
  );

  it("los cinco motivos que el registro produce hoy estan cubiertos", () => {
    // Si el registro cambia y deja de producir alguno, es informacion: quiere decir que esa
    // rama del puerto ya no la contrasta nadie.
    const motivos = new Set(fixture.vectores.filter((v) => !v.puede).map((v) => v.motivo));
    expect(motivos).toEqual(
      new Set([
        "agente_sin_encender",
        "agente_no_disponible",
        "permiso_denegado",
        "encargo_ambiguo",
      ]),
    );
  });
});

describe("la pausa gana sobre todo", () => {
  // No sale en los vectores a proposito: taparia el resto. Se prueba aqui, y se prueba que
  // tape incluso lo que ya seria un "no" por otra razon — porque el orden importa: si la
  // pausa se comprobara al final, la pantalla diria "a este agente le faltan condiciones"
  // cuando la verdad es que la oficina esta detenida.
  const EN_PAUSA = {
    activa: true,
    desde: "2026-08-23T19:06:50Z",
    por: "Gabriel",
    motivo: "Pausa de pruebas",
    seReanudaCuando: "todos los agentes esten activos",
  };

  const completo = (agenteId: string): Borrador => ({
    agenteId,
    titulo: fixture.borrador_completo.titulo!,
    descripcion: fixture.borrador_completo.descripcion!,
    entregableEsperado: fixture.borrador_completo.entregable_esperado!,
    hitl: false,
  });

  it("rechaza incluso a un agente que si se podria convocar", () => {
    const convocable = fixture.vectores.find((v) => v.puede)!;
    const veredicto = puedeConvocar({
      borrador: completo(convocable.agente),
      persona: resolverPersona("Gabriel", reg),
      registro: reg,
      pausa: EN_PAUSA,
    });
    expect(veredicto.puede).toBe(false);
    if (!veredicto.puede) expect(veredicto.motivo).toBe("oficina_en_pausa");
  });

  it("el mensaje trae el motivo y la condicion de reanudacion", () => {
    // Sin la condicion, quien lo lee no sabe que tiene que pasar para poder trabajar.
    const veredicto = puedeConvocar({
      borrador: completo("D5-01"),
      persona: resolverPersona("Gabriel", reg),
      registro: reg,
      pausa: EN_PAUSA,
    });
    if (veredicto.puede) throw new Error("deberia rechazar");
    expect(veredicto.detalle).toContain("Pausa de pruebas");
    expect(veredicto.detalle).toContain("todos los agentes esten activos");
    expect(veredicto.detalle).toContain("Gabriel");
  });

  it("gana incluso sobre un agente que no existe", () => {
    const veredicto = puedeConvocar({
      borrador: completo("NO-EXISTE"),
      persona: resolverPersona("Gabriel", reg),
      registro: reg,
      pausa: EN_PAUSA,
    });
    if (veredicto.puede) throw new Error("deberia rechazar");
    expect(veredicto.motivo).toBe("oficina_en_pausa");
  });
});

describe("un agente retirado", () => {
  // Hoy no hay ninguno en el registro, asi que no sale en los vectores. La rama existe y
  // tiene que seguir funcionando el dia que se retire al primero — que es exactamente
  // cuando nadie se acordaria de probarla.
  const retirado = {
    ...Object.values(reg.agentes)[0]!,
    id: "D9-99",
    retirado: true,
    listo: false,
    disponible: false,
    invocablePor: [],
    retiro: {
      fecha: "2026-03-01",
      por: "Gabriel",
      motivo: "Su trabajo lo absorbio svc-pricing.",
      lo_cubre: "D4-03",
    },
  };
  const registroConRetirado = { ...reg, agentes: { ...reg.agentes, "D9-99": retirado } };

  it("no se convoca, y el motivo no es «todavia no»", () => {
    const veredicto = puedeConvocar({
      borrador: {
        agenteId: "D9-99",
        titulo: "x",
        descripcion: "y",
        entregableEsperado: "z",
        hitl: false,
      },
      persona: resolverPersona("Gabriel", registroConRetirado),
      registro: registroConRetirado,
      pausa: ABIERTA,
    });
    if (veredicto.puede) throw new Error("deberia rechazar");
    expect(veredicto.motivo).toBe("agente_retirado");
    // Decirle "todavia no" a alguien cuyo agente se retiro lo manda a esperar algo que no
    // va a pasar. El mensaje tiene que decir quien cubre ese trabajo ahora.
    expect(veredicto.detalle).toContain("D4-03");
  });
});

describe("un encargo con firma humana", () => {
  it("entra como caso critico, no como uno normal", () => {
    // Su SLA en la bandeja se mide en horas habiles, no en dias (§7.3). Si entrara como
    // `media`, un encargo que necesita firma esperaria mas que uno que no la necesita.
    const convocable = fixture.vectores.find((v) => v.puede)!;
    const base = {
      agenteId: convocable.agente,
      titulo: fixture.borrador_completo.titulo!,
      descripcion: fixture.borrador_completo.descripcion!,
      entregableEsperado: fixture.borrador_completo.entregable_esperado!,
    };
    const persona = resolverPersona("Gabriel", reg);

    const conHitl = puedeConvocar({ borrador: { ...base, hitl: true }, persona, registro: reg, pausa: ABIERTA });
    const sinHitl = puedeConvocar({ borrador: { ...base, hitl: false }, persona, registro: reg, pausa: ABIERTA });

    expect(conHitl.puede && conHitl.criticidad).toBe("alta");
    expect(sinHitl.puede && sinHitl.criticidad).toBe("media");
  });
});

describe("a quien se le puede ofrecer en la pantalla", () => {
  it("solo agentes vivos, encendidos y que esta persona puede convocar", () => {
    const deGabriel = convocablesPor(resolverPersona("Gabriel", reg), reg);
    expect(deGabriel.length).toBeGreaterThan(0);
    for (const a of deGabriel) {
      expect(a.retirado).toBe(false);
      expect(a.disponible).toBe(true);
    }
  });

  it("coincide con lo que el veredicto concede, sin ofrecer lo que luego rechaza", () => {
    // Una lista que ofrece opciones que el servidor va a rechazar entrena a la gente a
    // ignorar los errores.
    const persona = resolverPersona("Gabriel", reg);
    for (const a of convocablesPor(persona, reg)) {
      const veredicto = puedeConvocar({
        borrador: {
          agenteId: a.id,
          titulo: fixture.borrador_completo.titulo!,
          descripcion: fixture.borrador_completo.descripcion!,
          entregableEsperado: fixture.borrador_completo.entregable_esperado!,
          hitl: false,
        },
        persona,
        registro: reg,
        pausa: ABIERTA,
      });
      expect(veredicto.puede, `${a.id} se ofrece pero se rechaza`).toBe(true);
    }
  });
});
