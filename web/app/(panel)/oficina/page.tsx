import { historialDePausas } from "@/lib/db/consultas";
import { sesion } from "@/lib/sesion";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";
import { Controles } from "./Controles";

export const dynamic = "force-dynamic";

const cuando = (fecha: Date | string): string =>
  new Date(fecha).toISOString().replace("T", " ").slice(0, 16);

/**
 * Pausa de la oficina (vista 9). Solo Direccion escribe; todos leen.
 *
 * Se lee entera a proposito, incluido el historial. Una pausa que solo se ve mientras esta
 * activa deja el sistema sin memoria de por que se detuvo en marzo — y esa es justo la
 * pregunta que se hace despues, no durante.
 */
export default async function Oficina() {
  const s = await sesion();
  const historial = await historialDePausas();
  const esDireccion = s.estado === "vinculada" && s.persona.rol === "direccion";

  const activa = historial.ok ? historial.datos.find((p) => p.hasta === null) : undefined;

  return (
    <>
      <div className="encabezado">
        <h1>Pausa de la oficina</h1>
        <p>
          Mientras haya una pausa activa, el runtime rechaza toda convocatoria. Lo que ya
          esta abierto no se cierra ni se pierde: queda donde estaba. Las memorias, los
          encargos y el registro no se tocan.
        </p>
      </div>

      {!historial.ok ? (
        <SinDatos
          motivo={historial.motivo}
          detalle={historial.detalle}
          queMostraria="si la oficina esta en pausa ahora mismo, y el historial completo con el motivo y el levantamiento de cada una"
        />
      ) : (
        <>
          <div className={activa ? "aviso" : "tarjeta"} style={{ marginBottom: 22 }}>
            {activa ? (
              <>
                <strong>La oficina esta en pausa</strong> desde {cuando(activa.desde)} UTC, por{" "}
                {activa.por_nombre ?? "alguien que ya no esta en personas"}.
                <p className="nota" style={{ marginTop: 8 }}>
                  <strong>Motivo:</strong> {activa.motivo}
                </p>
                <p className="nota">
                  <strong>Se reanuda cuando:</strong> {activa.se_reanuda_cuando}
                </p>
              </>
            ) : (
              <p style={{ margin: 0 }}>
                La oficina esta <strong>activa</strong>. No hay ninguna pausa abierta.
              </p>
            )}
          </div>

          <div className="tarjeta" style={{ marginBottom: 26 }}>
            <Controles pausada={Boolean(activa)} esDireccion={esDireccion} />
          </div>

          <h2 style={{ marginBottom: 12 }}>Historial</h2>
          {historial.datos.length === 0 ? (
            <VacioDeVerdad>
              Sin pausas registradas. La oficina tuvo una en agosto de 2026, ya levantada, que
              entra con la siembra inicial (<code>scripts/migrar_a_postgres.py</code>).
            </VacioDeVerdad>
          ) : (
            <div className="tarjeta desplaza">
              <table>
                <thead>
                  <tr>
                    <th>Desde</th>
                    <th>Hasta</th>
                    <th>Por</th>
                    <th>Motivo</th>
                    <th>Se reanudaba cuando</th>
                    <th>Se levanto porque</th>
                  </tr>
                </thead>
                <tbody>
                  {historial.datos.map((p) => (
                    <tr key={p.id}>
                      <td className="nota">{cuando(p.desde)}</td>
                      <td className="nota">
                        {p.hasta ? cuando(p.hasta) : <span className="alarma">abierta</span>}
                      </td>
                      <td>{p.por_nombre ?? "—"}</td>
                      <td>{p.motivo}</td>
                      <td className="nota">{p.se_reanuda_cuando}</td>
                      {/* El levantamiento en la MISMA fila que el motivo. Separados, en un
                          mes nadie sabria si se cumplio la condicion o si hacia falta
                          trabajar. */}
                      <td className="nota">
                        {p.reanudada_porque ?? "—"}
                        {p.reanudada_por_nombre && (
                          <div>por {p.reanudada_por_nombre}</div>
                        )}
                      </td>
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
