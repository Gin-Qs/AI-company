import { cargarAgentes, cargarEquipos } from "@/lib/registro";
import { cargarGate, resolverPersona, responsableDe, type Registro } from "@/lib/rbac";

export const dynamic = "force-dynamic";

const CLASE: Record<string, string> = {
  built: "p-built",
  listo: "p-listo",
  planned: "p-planned",
  retirado: "p-retirado",
  disponible: "p-built",
};

export default async function Agentes() {
  const registro: Registro = {
    agentes: cargarAgentes(),
    equipos: cargarEquipos(),
    gate: cargarGate(),
  };

  const dominio = Object.values(registro.agentes)
    .filter((a) => a.tipo === "dominio")
    .sort((a, b) => a.id.localeCompare(b.id));

  return (
    <>
      <div className="encabezado">
        <h1>Agentes</h1>
        <p>
          Los agentes de dominio declarados en <code>registry/agents/</code>. La columna
          &laquo;responde&raquo; se deriva en vivo: agente &rarr; equipo &rarr;{" "}
          <code>owner_humano</code>. Si cambia un owner en el registro, cambia aqui.
        </p>
      </div>

      <div className="tarjeta desplaza">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Puesto</th>
              <th>Estado</th>
              <th>Fase</th>
              <th>Equipo</th>
              <th>Responde</th>
            </tr>
          </thead>
          <tbody>
            {dominio.map((a) => (
              <tr key={a.id}>
                <td>
                  <code>{a.id}</code>
                  {a.identidad && (
                    <div className="nota">{a.identidad.nombre}</div>
                  )}
                </td>
                <td>
                  {a.nombre}
                  <div className="nota">{a.mision.slice(0, 110)}</div>
                </td>
                <td>
                  <span className={`pildora ${CLASE[a.estado] ?? "p-planned"}`}>
                    {a.estado}
                  </span>
                </td>
                <td>{a.fase ?? "—"}</td>
                <td>{a.equipos.join(", ") || "—"}</td>
                <td>{responsableDe(a.id, registro) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
