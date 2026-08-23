import Link from "next/link";

import { buscarCasos, casosPorEstado } from "@/lib/db/consultas";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";

export const dynamic = "force-dynamic";

/** Los ocho estados de `services/runlog/caso.py`, con el color que ya usa el resto del portal. */
const CLASE: Record<string, string> = {
  recibido: "p-planned",
  en_proceso: "p-listo",
  esperando_validacion: "p-listo",
  rechazado_validacion: "p-retirado",
  esperando_humano: "p-listo",
  entregado: "p-built",
  bloqueado: "p-retirado",
  expirado: "p-retirado",
};

const cuando = (fecha: Date | string): string =>
  new Date(fecha).toISOString().replace("T", " ").slice(0, 16);

export default async function Casos({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  const [casos, porEstado] = await Promise.all([buscarCasos(q), casosPorEstado()]);

  return (
    <>
      <div className="encabezado">
        <h1>Casos</h1>
        <p>
          Buscador de <code>trace_id</code>. Cada caso es el plegado de sus eventos, no una
          fila que alguien actualizo: por eso su historia completa siempre se puede volver a
          leer, y el estado de ayer se puede volver a calcular.
        </p>
      </div>

      {/* Un GET, no un formulario con estado: la busqueda queda en la URL y se puede
          compartir. "Mira este caso" es un enlace, no una instruccion. */}
      <form method="get" className="buscador">
        <input
          type="search"
          name="q"
          defaultValue={q}
          placeholder="TR-20260818-001, E-001, D4-03, cotizacion..."
          aria-label="Buscar por trace, referencia, responsable o tipo"
        />
        <button type="submit">Buscar</button>
        {q && (
          <Link href="/casos" className="nota">
            limpiar
          </Link>
        )}
      </form>

      {!casos.ok ? (
        <SinDatos
          motivo={casos.motivo}
          detalle={casos.detalle}
          queMostraria="los casos con su estado, tiempo por paso, reintentos y escalamientos"
        />
      ) : (
        <>
          {porEstado.ok && porEstado.datos.length > 0 && (
            <section className="rejilla">
              {porEstado.datos.map((e) => (
                <div className="tarjeta" key={e.estado}>
                  <div className="cifra">{e.cuantos}</div>
                  <div className="etiqueta">{e.estado.replace(/_/g, " ")}</div>
                </div>
              ))}
            </section>
          )}

          {casos.datos.length === 0 ? (
            <VacioDeVerdad>
              {q
                ? `Ningun caso coincide con "${q}". La base respondio; simplemente no hay nada que empate.`
                : "La base esta conectada y no tiene casos todavia. Es lo esperado hasta que corra la siembra inicial (scripts/migrar_a_postgres.py)."}
            </VacioDeVerdad>
          ) : (
            <div className="tarjeta desplaza">
              <table>
                <thead>
                  <tr>
                    <th>Trace</th>
                    <th>Tipo</th>
                    <th>Referencia</th>
                    <th>Estado</th>
                    <th>Responsable</th>
                    <th>Pasos</th>
                    <th>Reintentos</th>
                    <th>Escalamientos</th>
                    <th>Actualizado</th>
                  </tr>
                </thead>
                <tbody>
                  {casos.datos.map((c) => (
                    <tr key={c.trace_id}>
                      <td>
                        <Link href={`/casos/${c.trace_id}`}>
                          <code>{c.trace_id}</code>
                        </Link>
                      </td>
                      <td>{c.tipo}</td>
                      <td>
                        <code>{c.referencia}</code>
                      </td>
                      <td>
                        <span className={`pildora ${CLASE[c.estado] ?? ""}`}>
                          {c.estado.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>
                        <code>{c.responsable || "-"}</code>
                      </td>
                      <td>{c.pasos}</td>
                      {/* Dos reintentos es el tope de caso.py; el tercero bloquea. Se
                          marca para que se vea antes de que pase, no despues. */}
                      <td className={c.reintentos >= 2 ? "alarma" : undefined}>
                        {c.reintentos}
                      </td>
                      <td className={c.escalamientos > 0 ? "alarma" : undefined}>
                        {c.escalamientos}
                      </td>
                      <td className="nota">{cuando(c.actualizado_en)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}
