/**
 * El lector de `.ics`.
 *
 * Un parser escrito a mano es facil de equivocar de formas que no se ven: una linea plegada
 * que corta el motivo a la mitad, una fecha con hora que se cuela como dia completo, un
 * archivo con CRLF que deja `\r` pegado al final de cada valor. Cada una de esas produce un
 * calendario **plausible y equivocado**, y un calendario equivocado vence aprobaciones el dia
 * que no toca.
 */

import { describe, expect, it } from "vitest";

import { leerIcs } from "./ics";

/** Como lo exporta Outlook: CRLF de verdad. */
const ics = (...lineas: string[]) =>
  ["BEGIN:VCALENDAR", "VERSION:2.0", ...lineas, "END:VCALENDAR"].join("\r\n");

const evento = (...lineas: string[]) => ["BEGIN:VEVENT", ...lineas, "END:VEVENT"];

describe("los eventos de dia completo", () => {
  it("se leen con su fecha y su motivo", () => {
    const { eventos } = leerIcs(
      ics(...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Dia de la Independencia", "UID:abc-1")),
    );
    expect(eventos).toEqual([
      { fecha: "2026-09-16", motivo: "Dia de la Independencia", uid: "abc-1" },
    ]);
  });

  it("aceptan un DTSTART sin VALUE=DATE mientras no traiga hora", () => {
    // No todos los calendarios ponen el parametro. Si solo hay ocho digitos, es un dia.
    const { eventos } = leerIcs(ics(...evento("DTSTART:20260101", "SUMMARY:Ano Nuevo")));
    expect(eventos[0]?.fecha).toBe("2026-01-01");
  });

  it("salen ordenados por fecha aunque el archivo venga desordenado", () => {
    const { eventos } = leerIcs(
      ics(
        ...evento("DTSTART;VALUE=DATE:20261225", "SUMMARY:Navidad"),
        ...evento("DTSTART;VALUE=DATE:20260101", "SUMMARY:Ano Nuevo"),
      ),
    );
    expect(eventos.map((e) => e.fecha)).toEqual(["2026-01-01", "2026-12-25"]);
  });

  it("un evento sin UID entra igual, con uid nulo", () => {
    // El UID sirve para reimportar sin duplicar; no tenerlo no invalida el feriado.
    const { eventos } = leerIcs(ics(...evento("DTSTART;VALUE=DATE:20260501", "SUMMARY:Dia del Trabajo")));
    expect(eventos[0]?.uid).toBeNull();
  });
});

describe("lo que se deja fuera, y se dice", () => {
  it("un evento con hora no vuelve inhabil el dia", () => {
    // Si el archivo trae la agenda completa de alguien, cada junta convertiria ese dia en
    // feriado y alargaria todos los SLA de la semana.
    const { eventos, omitidos } = leerIcs(
      ics(...evento("DTSTART:20260310T150000Z", "SUMMARY:Junta con el cliente")),
    );
    expect(eventos).toHaveLength(0);
    expect(omitidos.join(" ")).toMatch(/tiene hora/);
  });

  it("un evento sin fecha se omite nombrandolo", () => {
    const { eventos, omitidos } = leerIcs(ics(...evento("SUMMARY:Algo sin fecha")));
    expect(eventos).toHaveLength(0);
    expect(omitidos.join(" ")).toContain("Algo sin fecha");
  });

  it("una repeticion se avisa en vez de expandirse", () => {
    // Evaluar mal una RRULE significa un feriado el dia equivocado durante años.
    const { omitidos } = leerIcs(
      ics(...evento("DTSTART;VALUE=DATE:20260101", "SUMMARY:Ano Nuevo", "RRULE:FREQ=YEARLY")),
    );
    expect(omitidos.join(" ")).toMatch(/repeticion|RRULE/i);
  });

  it("el mismo dia dos veces entra una sola vez, y se dice", () => {
    const { eventos, omitidos } = leerIcs(
      ics(
        ...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Independencia"),
        ...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Independencia (duplicado)"),
      ),
    );
    expect(eventos).toHaveLength(1);
    expect(omitidos.join(" ")).toContain("ya venia en este archivo");
  });

  it("`omitidos` esta vacio cuando no se dejo nada fuera", () => {
    // Una lista de omitidos que siempre trae algo entrena a ignorarla.
    const { omitidos } = leerIcs(ics(...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:X")));
    expect(omitidos).toEqual([]);
  });
});

describe("las trampas del formato", () => {
  it("deshace el plegado de lineas de RFC 5545", () => {
    // Sin esto el motivo llega cortado a los 75 octetos, que es el fallo mas facil de no
    // notar: el feriado entra bien y el nombre sale a medias.
    const crudo =
      "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20260916\r\n" +
      "SUMMARY:Dia de la Independencia de los Estados Unidos\r\n  Mexicanos\r\n" +
      "END:VEVENT\r\nEND:VCALENDAR";
    const { eventos } = leerIcs(crudo);
    expect(eventos[0]?.motivo).toBe("Dia de la Independencia de los Estados Unidos Mexicanos");
  });

  it("no deja el retorno de carro pegado al valor", () => {
    const { eventos } = leerIcs(ics(...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Independencia", "UID:u-9")));
    expect(eventos[0]?.uid).toBe("u-9");
    expect(eventos[0]?.motivo).not.toMatch(/[\r\n]/);
  });

  it("desescapa comas y puntos y comas", () => {
    const { eventos } = leerIcs(
      ics(...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Independencia\\, dia completo")),
    );
    expect(eventos[0]?.motivo).toBe("Independencia, dia completo");
  });

  it("acepta nombres de propiedad en minusculas", () => {
    const { eventos } = leerIcs(
      ["BEGIN:VCALENDAR", "begin:vevent", "dtstart;value=date:20260916", "summary:Independencia", "end:vevent", "END:VCALENDAR"].join("\r\n"),
    );
    expect(eventos[0]?.fecha).toBe("2026-09-16");
  });

  it("ignora lo que este fuera de un VEVENT", () => {
    // Un VTIMEZONE trae DTSTART propios. Sin este filtro entrarian como feriados.
    const crudo = [
      "BEGIN:VCALENDAR",
      "BEGIN:VTIMEZONE",
      "DTSTART:19700101T000000",
      "SUMMARY:No soy un feriado",
      "END:VTIMEZONE",
      ...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:Independencia"),
      "END:VCALENDAR",
    ].join("\r\n");
    const { eventos } = leerIcs(crudo);
    expect(eventos).toHaveLength(1);
    expect(eventos[0]?.motivo).toBe("Independencia");
  });

  it("un archivo vacio o sin eventos no revienta", () => {
    expect(leerIcs("").eventos).toEqual([]);
    expect(leerIcs("cualquier cosa").eventos).toEqual([]);
    expect(leerIcs(ics()).eventos).toEqual([]);
  });

  it("un evento sin SUMMARY entra con un nombre declarado, no vacio", () => {
    const { eventos } = leerIcs(ics(...evento("DTSTART;VALUE=DATE:20260916")));
    expect(eventos[0]?.motivo).toBe("(sin titulo)");
  });
});

describe("la fecha no arrastra el huso", () => {
  it("el 16 de septiembre es el 16 sin importar donde corra esto", () => {
    // Si el parser construyera un `Date`, en UTC-6 el 20260916 podria volver como el 15.
    // Por eso la fecha viaja como texto de punta a punta.
    const { eventos } = leerIcs(ics(...evento("DTSTART;VALUE=DATE:20260916", "SUMMARY:X")));
    expect(eventos[0]?.fecha).toBe("2026-09-16");
    expect(typeof eventos[0]?.fecha).toBe("string");
  });
});
