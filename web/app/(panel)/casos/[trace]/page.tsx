import Link from "next/link";
import { notFound } from "next/navigation";

import { historiaDe, unCaso, type Evento } from "@/lib/db/consultas";

import { sesion } from "@/lib/sesion";

import { SinDatos } from "../../_componentes/SinDatos";
import { Avanzar } from "./Avanzar";

export const dynamic = "force-dynamic";

const cuando = (fecha: Date | string): string =>
  new Date(fecha).toISOString().replace("T", " ").slice(0, 19);

/**
 * Cuanto tardo cada paso: la distancia al evento anterior del MISMO caso.
 *
 * Se calcula aqui y no en SQL a proposito. Es aritmetica de presentacion —restar dos fechas
 * que ya vienen ordenadas por `seq`— y meterla en la consulta la escondería detras de una
 * window function que nadie vuelve a leer. El primer evento no tiene anterior: su duracion
 * es `null`, no cero. Cero seria afirmar que fue instantaneo.
 */
const duraciones = (eventos: Evento[]): (number | null)[] =>
  eventos.map((e, i) => {
    const anterior = eventos[i - 1];
    return anterior ? new Date(e.ts).getTime() - new Date(anterior.ts).getTime() : null;
  });

const legible = (ms: number | null): string => {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms} ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h} h ${m % 60} min`;
};

/** Lo que el evento hizo, en una linea, sin obligar a abrir el JSON. */
const resumen = (e: Evento): string => {
  const d = e.datos ?? {};
  if (e.evento === "apertura") return `abre ${d.tipo ?? ""} ${d.referencia ?? ""}`.trim();
  if (e.evento === "transicion") {
    const motivo = d.motivo ? ` — ${d.motivo}` : "";
    return `${d.de} → ${d.a}${motivo}`;
  }
  const resultado = d.resultado && d.resultado !== "ok" ? ` (${d.resultado})` : "";
  return `${d.tipo ?? "paso"}${resultado}`;
};

export default async function DetalleDeCaso({
  params,
}: {
  params: Promise<{ trace: string }>;
}) {
  const { trace } = await params;
  const [caso, historia, s] = await Promise.all([unCaso(trace), historiaDe(trace), sesion()]);

  if (!caso.ok) {
    return (
      <>
        <div className="encabezado">
          <h1>
            <code>{trace}</code>
          </h1>
        </div>
        <SinDatos
          motivo={caso.motivo}
          detalle={caso.detalle}
          queMostraria="el estado del caso y su historia completa, evento por evento"
        />
      </>
    );
  }

  // Hay base, la consulta corrio y este trace no existe. Eso si es un 404 de verdad.
  if (caso.datos === null) notFound();

  const c = caso.datos;
  const eventos = historia.ok ? historia.datos : [];
  const tiempos = duraciones(eventos);

  return (
    <>
      <div className="encabezado">
        <p className="nota">
          <Link href="/casos">&larr; Casos</Link>
        </p>
        <h1>
          <code>{c.trace_id}</code>
        </h1>
        <p>
          {c.tipo} sobre <code>{c.referencia}</code>, criticidad {c.criticidad}. Abierto el{" "}
          {cuando(c.abierto_en)}.
        </p>
      </div>

      <section className="rejilla">
        <div className="tarjeta">
          <div className="cifra" style={{ fontSize: 22 }}>
            {c.estado.replace(/_/g, " ")}
          </div>
          <div className="etiqueta">Estado</div>
          <p className="nota">Responsable: {c.responsable || "sin declarar"}</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{c.pasos}</div>
          <div className="etiqueta">Pasos</div>
          <p className="nota">{eventos.length} eventos en total, con aperturas y transiciones.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{c.reintentos}</div>
          <div className="etiqueta">Reintentos</div>
          <p className="nota">
            El tope son 2 (<code>caso.py</code>). Al tercer rechazo el caso se bloquea y lo
            mira una persona.
          </p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{c.escalamientos}</div>
          <div className="etiqueta">Escalamientos</div>
          <p className="nota">Ninguna accion al vencer un SLA es &laquo;aprobar&raquo;.</p>
        </div>
      </section>

      {/* Mover el caso. Es lo que llena la bandeja: un encargo convocado nace en
          `recibido` y alguien tiene que empezarlo y mandarlo a firma. */}
      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Mover el caso</h2>
      <div className="tarjeta" style={{ marginBottom: 8 }}>
        {s.estado === "vinculada" ? (
          <Avanzar
            traceId={c.trace_id}
            agenteId={c.responsable}
            estado={c.estado}
            ultimoSeqVisto={c.ultimo_seq}
          />
        ) : (
          <p className="nota">
            Mover un caso queda registrado con tu nombre, y no se puede sin saber quien eres
            en el registro.
          </p>
        )}
      </div>

      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Historia</h2>
      <p className="nota" style={{ marginBottom: 14 }}>
        En orden de <code>seq</code>, no de fecha: dos eventos pueden compartir el segundo, y
        ordenar por reloj reordenaria la historia. Consumo del caso: {c.tokens} tokens,{" "}
        {c.costo_mxn} MXN.
      </p>

      {!historia.ok ? (
        <SinDatos
          motivo={historia.motivo}
          detalle={historia.detalle}
          queMostraria="cada evento del caso con su actor, su autor y cuanto tardo"
        />
      ) : (
        <div className="tarjeta desplaza">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Evento</th>
                <th>Que paso</th>
                <th>Actor</th>
                <th>Autor</th>
                <th>Cuando</th>
                <th>Tardo</th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((e, i) => (
                <tr key={e.seq}>
                  <td>{e.seq}</td>
                  <td>{e.evento}</td>
                  <td>{resumen(e)}</td>
                  <td>
                    <code>{e.actor}</code>
                  </td>
                  {/* Una persona o nadie. Un agente NO aparece aqui: `autor_persona` es
                      quien lo hizo si fue una persona, y llenarlo con el agente convertiria
                      la auditoria en una suposicion. */}
                  <td>{e.autor_nombre ?? <span className="nota">—</span>}</td>
                  <td className="nota">{cuando(e.ts)}</td>
                  <td className="nota">{legible(tiempos[i] ?? null)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
