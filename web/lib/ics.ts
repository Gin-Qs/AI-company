/**
 * Lee un archivo `.ics` y saca de el los dias festivos.
 *
 * POR QUE UN ARCHIVO Y NO UNA SINCRONIZACION CON OUTLOOK. El calendario decide **cuando
 * vencen las aprobaciones**. Si dependiera de un servicio externo en vivo, alguien moviendo
 * un evento en su calendario cambiaria en silencio cuando expira un HITL, y el dia que ese
 * servicio no respondiera el SLA se quedaria sin saber que dia es habil. Un `.ics` exportado
 * es un dato que se mira antes de aceptarlo, se guarda con autor y fecha, y no cambia solo.
 * Importar es una decision; sincronizar es una dependencia.
 *
 * Se implementa a mano y no con una libreria porque lo que hace falta es minusculo —tres
 * campos de los eventos de dia completo— y una dependencia nueva en la ruta del SLA tiene
 * que ganarselo.
 *
 * LO QUE SE IGNORA A PROPOSITO:
 *
 *   * Los eventos con hora. Un feriado es un dia entero; una junta de las 3 no lo es. Si el
 *     archivo trae la agenda completa de alguien, esto toma solo lo que parece un feriado en
 *     vez de convertir cada reunion en un dia inhabil.
 *   * `RRULE`. Una regla de repeticion habria que evaluarla, y evaluarla mal significa un
 *     feriado el dia equivocado durante anos. Se declara lo que el archivo dice literalmente.
 */

export interface EventoIcs {
  /** "AAAA-MM-DD". Fecha de calendario, sin huso: un feriado no empieza a una hora. */
  fecha: string;
  motivo: string;
  /** El `UID` del evento, para poder reimportar el mismo archivo sin duplicar. */
  uid: string | null;
}

export interface LecturaIcs {
  eventos: EventoIcs[];
  /** Lo que se dejo fuera y por que. Se enseña: un import silencioso esconde lo que perdio. */
  omitidos: string[];
}

/**
 * Deshace el plegado de lineas del formato iCalendar.
 *
 * RFC 5545 corta las lineas largas a 75 octetos y continua la siguiente con un espacio o un
 * tabulador. Sin deshacerlo, un `SUMMARY` largo llega partido y el motivo del feriado sale a
 * medias — el fallo mas facil de no notar al leer este formato.
 */
const desplegar = (texto: string): string[] => {
  const lineas: string[] = [];
  for (const cruda of texto.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n")) {
    if ((cruda.startsWith(" ") || cruda.startsWith("\t")) && lineas.length > 0) {
      lineas[lineas.length - 1] += cruda.slice(1);
    } else {
      lineas.push(cruda);
    }
  }
  return lineas;
};

/** `DTSTART;VALUE=DATE:20260916` -> `{ propiedad: "DTSTART", params: ";VALUE=DATE", valor: "20260916" }` */
const partir = (linea: string): { propiedad: string; params: string; valor: string } | null => {
  const dosPuntos = linea.indexOf(":");
  if (dosPuntos < 0) return null;
  const izquierda = linea.slice(0, dosPuntos);
  const puntoYComa = izquierda.indexOf(";");
  return {
    propiedad: (puntoYComa < 0 ? izquierda : izquierda.slice(0, puntoYComa)).toUpperCase(),
    params: puntoYComa < 0 ? "" : izquierda.slice(puntoYComa).toUpperCase(),
    valor: linea.slice(dosPuntos + 1),
  };
};

/** El texto de iCalendar escapa comas, puntos y comas, barras y saltos de linea. */
const desescapar = (v: string): string =>
  v
    .replace(/\\n/gi, " ")
    .replace(/\\([,;\\])/g, "$1")
    .split(/\s+/)
    .join(" ")
    .trim();

export const leerIcs = (contenido: string): LecturaIcs => {
  const eventos: EventoIcs[] = [];
  const omitidos: string[] = [];

  let dentro = false;
  let fecha: string | null = null;
  let conHora = false;
  let motivo = "";
  let uid: string | null = null;

  const cerrar = () => {
    const nombre = motivo || "(sin titulo)";
    if (conHora) {
      // Un feriado es un dia entero. Convertir una junta de las 3 en dia inhabil alargaria
      // todos los SLA de ese dia sin que nadie lo pidiera.
      omitidos.push(`${nombre}: tiene hora, no es un dia completo`);
    } else if (!fecha) {
      omitidos.push(`${nombre}: sin fecha de inicio legible`);
    } else {
      eventos.push({ fecha, motivo: nombre, uid });
    }
    fecha = null;
    conHora = false;
    motivo = "";
    uid = null;
  };

  for (const linea of desplegar(contenido)) {
    const p = partir(linea.trim());
    if (!p) continue;

    if (p.propiedad === "BEGIN" && p.valor.toUpperCase() === "VEVENT") {
      dentro = true;
      continue;
    }
    if (p.propiedad === "END" && p.valor.toUpperCase() === "VEVENT") {
      if (dentro) cerrar();
      dentro = false;
      continue;
    }
    if (!dentro) continue;

    if (p.propiedad === "DTSTART") {
      const soloFecha = /^(\d{4})(\d{2})(\d{2})$/.exec(p.valor.trim());
      if (soloFecha && (p.params.includes("VALUE=DATE") || !p.valor.includes("T"))) {
        fecha = `${soloFecha[1]}-${soloFecha[2]}-${soloFecha[3]}`;
      } else {
        conHora = true;
        // Se conserva la fecha para poder nombrar lo omitido con algo util.
        const conT = /^(\d{4})(\d{2})(\d{2})T/.exec(p.valor.trim());
        if (conT) fecha = `${conT[1]}-${conT[2]}-${conT[3]}`;
      }
    } else if (p.propiedad === "SUMMARY") {
      motivo = desescapar(p.valor);
    } else if (p.propiedad === "UID") {
      uid = p.valor.trim() || null;
    } else if (p.propiedad === "RRULE") {
      // Se declara lo que el archivo dice literalmente. Evaluar una regla de repeticion mal
      // significa un feriado el dia equivocado durante anos.
      omitidos.push(
        `${motivo || "(sin titulo)"}: declara una repeticion (RRULE) que no se expande; ` +
          `solo entra la primera fecha`,
      );
    }
  }

  // Un archivo puede traer el mismo dia dos veces. Gana el primero, y se dice.
  const porFecha = new Map<string, EventoIcs>();
  for (const e of eventos) {
    if (porFecha.has(e.fecha)) {
      omitidos.push(`${e.motivo}: el ${e.fecha} ya venia en este archivo`);
      continue;
    }
    porFecha.set(e.fecha, e);
  }

  return {
    eventos: [...porFecha.values()].sort((a, b) => a.fecha.localeCompare(b.fecha)),
    omitidos,
  };
};
