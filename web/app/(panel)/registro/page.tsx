import {
  ultimaValidacion,
  ultimaValidacionDeCualquierRama,
  type ReglaValidada,
  type Validacion,
} from "@/lib/db/consultas";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";

export const dynamic = "force-dynamic";

/**
 * Los CUATRO estados de §2.1, y por que son cuatro.
 *
 * Un validador que pinta "omitida" de verde miente por optimismo; uno que la pinta de rojo
 * entrena al equipo a ignorar el rojo. Y "pendiente de fase futura" no es ninguna de las dos:
 * es una regla que pasa hoy y tiene trabajo declarado para despues.
 */
const CLASE: Record<string, string> = {
  OK: "p-built",
  FALLA: "p-retirado",
  OMITIDA: "p-planned",
  PENDIENTE: "p-listo",
};

/** El estado que se pinta: `pendientes` gana sobre un OK limpio, porque dice algo mas. */
const estadoVisible = (r: ReglaValidada): string =>
  r.estado === "OK" && r.pendientes.length > 0 ? "PENDIENTE" : r.estado;

export default async function SaludDelRegistro() {
  // Se prefiere `main`, que es lo que se despliega. Si nunca se ha publicado una corrida de
  // main —una rama nueva, un repositorio recien conectado— se cae a la ultima de cualquier
  // rama y la pantalla DICE de cual es. Ensenar la de otra rama como si fuera la de main
  // seria reportar la salud de un codigo que no esta desplegado.
  const deMain = await ultimaValidacion("main");
  const lectura =
    deMain.ok && deMain.datos === null ? await ultimaValidacionDeCualquierRama() : deMain;

  return (
    <>
      <div className="encabezado">
        <h1>Salud del registro</h1>
        <p>
          Las reglas de <code>scripts/validate_registry.py</code>, tal como las dejo la ultima
          corrida de la CI. El portal <strong>no</strong> las reimplementa: las lee. Cero
          duplicacion y cero deriva posible, a cambio de que lo que se ve es el estado del
          ultimo commit validado, no el de este instante.
        </p>
      </div>

      {!lectura.ok ? (
        <SinDatos
          motivo={lectura.motivo}
          detalle={lectura.detalle}
          queMostraria="las 17 reglas del registro con su estado, y el commit y la fecha de la ultima corrida de CI"
        />
      ) : lectura.datos === null ? (
        <VacioDeVerdad>
          La base esta conectada y <code>validacion_registro</code> no tiene ninguna corrida
          todavia. La escribe la CI (<code>.github/workflows/validar.yml</code>) en cada push,
          y necesita el secreto <code>DIRECT_URL</code> configurado en el repositorio. Hasta
          entonces el resultado queda solo como artefacto descargable de la corrida.
        </VacioDeVerdad>
      ) : (
        <Resultado v={lectura.datos} />
      )}
    </>
  );
}

function Resultado({ v }: { v: Validacion }) {
  const reglas = Array.isArray(v.reglas) ? v.reglas : [];
  const conPendientes = reglas.filter((r) => r.pendientes.length > 0).length;

  return (
    <>
      {/* LA FECHA Y EL COMMIT, ARRIBA Y NO EN LETRA CHICA. Una vista que no dice de cuando
          son sus datos se lee como si fueran de ahora. Ese es el costo aceptado de §11 y la
          unica forma de que sea aceptable es que este a la vista. */}
      <div className="tarjeta" style={{ marginBottom: 18 }}>
        <p style={{ margin: 0 }}>
          Ultima corrida: <strong>{new Date(v.corrido_en).toISOString().slice(0, 16).replace("T", " ")} UTC</strong>{" "}
          sobre <code>{v.commit_sha ? v.commit_sha.slice(0, 8) : "commit sin declarar"}</code> de{" "}
          <code>{v.rama || "rama sin declarar"}</code>.
        </p>
        <p className="nota" style={{ marginTop: 8 }}>
          {v.pytest_ok ? (
            <>
              La suite paso
              {v.pytest_total ? `: ${v.pytest_total} pruebas.` : ", sin decir cuantas pruebas corrieron."}
            </>
          ) : (
            <strong className="alarma">
              La suite NO paso en esta corrida
              {v.pytest_total ? ` (${v.pytest_total} pruebas).` : "."} Las reglas de abajo son de
              un commit cuyo codigo esta roto.
            </strong>
          )}
        </p>
      </div>

      <section className="rejilla">
        <div className="tarjeta">
          <div className="cifra">{v.en_verde}</div>
          <div className="etiqueta">En verde</div>
        </div>
        <div className="tarjeta">
          <div className={`cifra ${v.en_falla > 0 ? "alarma" : ""}`}>{v.en_falla}</div>
          <div className="etiqueta">En falla</div>
          <p className="nota">Reprueban el PR.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{v.omitidas}</div>
          <div className="etiqueta">Omitidas</div>
          <p className="nota">Sin insumo para correr. No es verde ni es rojo.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{v.pendientes}</div>
          <div className="etiqueta">Pendientes</div>
          <p className="nota">
            Trabajo declarado de fases futuras, repartido en {conPendientes}{" "}
            {conPendientes === 1 ? "regla" : "reglas"}.
          </p>
        </div>
      </section>

      <div className="tarjeta desplaza" style={{ marginTop: 22 }}>
        <table>
          <thead>
            <tr>
              <th>Regla</th>
              <th>Que comprueba</th>
              <th>Estado</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {reglas.map((r) => {
              const estado = estadoVisible(r);
              return (
                <tr key={r.numero}>
                  <td>
                    <code>{r.numero}</code>
                  </td>
                  <td>{r.descripcion}</td>
                  <td>
                    <span className={`pildora ${CLASE[estado] ?? ""}`}>{estado}</span>
                  </td>
                  <td className="nota">
                    {/* Se enseñan las tres cosas que el validador sabe y que un semaforo
                        binario tira a la basura: por que fallo, por que se omitio, y que
                        queda pendiente aunque hoy pase. */}
                    {r.fallas.map((f, i) => (
                      <div key={`f${i}`} className="alarma">
                        {f}
                      </div>
                    ))}
                    {r.omitida && <div>omitida: {r.omitida}</div>}
                    {r.pendientes.map((p, i) => (
                      <div key={`p${i}`}>pendiente: {p}</div>
                    ))}
                    {!r.fallas.length && !r.omitida && !r.pendientes.length && "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
