import { cargarAgentes, panorama } from "@/lib/registro";
import { cargarCalendario } from "@/lib/registro/politicas";

// El registro se lee del sistema de archivos en cada peticion: es la fuente de verdad y
// cambia por despliegue, no en caliente.
export const dynamic = "force-dynamic";

export default async function Resumen() {
  const agentes = cargarAgentes();
  const p = panorama(agentes);
  const calendario = cargarCalendario();

  return (
    <>
      <div className="encabezado">
        <h1>Resumen</h1>
        <p>
          Estado del registro, leido de <code>registry/</code>. Todavia sin datos de
          operacion: ningun agente esta encendido, asi que no hay casos ni consumo que
          mostrar.
        </p>
      </div>

      <section className="rejilla">
        <div className="tarjeta">
          <div className="cifra">{p.disponibles}</div>
          <div className="etiqueta">Encendidos</div>
          <p className="nota">Se pueden convocar hoy.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{p.listos}</div>
          <div className="etiqueta">Listos, sin encender</div>
          <p className="nota">Contrato completo, condiciones pendientes.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{p.planeados}</div>
          <div className="etiqueta">Planeados</div>
          <p className="nota">Declarados en el roadmap; aun no existen.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{p.consultores}</div>
          <div className="etiqueta">Consultores</div>
          <p className="nota">Disponibles siempre, sin ACT-*.</p>
        </div>
      </section>

      {calendario.festivos.size === 0 && (
        <div className="aviso">
          <strong>Calendario laboral sin calibrar.</strong> La lista de festivos esta vacia,
          asi que un HITL abierto la vispera de un feriado vencera ese mismo dia, cuando no
          haya nadie para atenderlo. Se llena en{" "}
          <code>registry/policies/calendario-laboral.yaml</code>. Jornada vigente:{" "}
          {calendario.horasPorDia} h, {calendario.diasHabiles.size} dias habiles.
        </div>
      )}

      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Lo que falta para encender</h2>
      <p className="nota" style={{ marginBottom: 14 }}>
        Cada condicion viene del registro del agente, con su responsable. Un agente completo
        y apagado es legitimo y peligroso: el trabajo esta hecho, nadie lo usa y la razon se
        olvida en dos semanas.
      </p>
      <div className="tarjeta desplaza">
        <table>
          <thead>
            <tr>
              <th>Agente</th>
              <th>Condicion pendiente</th>
              <th>Lo cierra</th>
            </tr>
          </thead>
          <tbody>
            {p.condicionesPendientes.map((c, i) => (
              <tr key={`${c.agente}-${i}`}>
                <td>
                  <code>{c.agente}</code>
                </td>
                <td>{c.condicion}</td>
                <td>{c.responsable}</td>
              </tr>
            ))}
            {p.condicionesPendientes.length === 0 && (
              <tr>
                <td colSpan={3}>Ninguna: todos los agentes listos ya se pueden encender.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
