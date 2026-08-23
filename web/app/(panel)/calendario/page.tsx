import { festivosDeclarados, type Festivo } from "@/lib/db/consultas";
import { cargarCalendario } from "@/lib/registro/politicas";
import { sesion } from "@/lib/sesion";

import { SinDatos } from "../_componentes/SinDatos";
import { Editor, Quitar } from "./Editor";

export const dynamic = "force-dynamic";

const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];

/**
 * Calendario laboral: el mecanismo en git, los feriados en la base.
 *
 * La separacion no es arbitraria. El huso, la jornada y los dias habiles son **politica**:
 * cambian casi nunca, y un horario que se edita desde una pantalla es un horario sin
 * auditoria. Los feriados son un **catalogo de la empresa** que cambia cada año y que nadie
 * iba a mantener por pull request — la prueba es que la lista llevaba vacia desde que existe
 * el calendario, con consecuencia real sobre los SLA.
 */
export default async function CalendarioLaboral() {
  const s = await sesion();
  const politica = cargarCalendario();
  const festivos = await festivosDeclarados();

  const puedeEditar =
    s.estado === "vinculada" && (s.persona.rol === "direccion" || s.persona.rol === "operador");

  // Agrupados por año: una lista corrida de tres años se vuelve ilegible, y el año es
  // justamente la unidad en la que se revisa un calendario laboral.
  const porAnio = new Map<string, Festivo[]>();
  if (festivos.ok) {
    for (const f of festivos.datos) {
      const anio = f.fecha.slice(0, 4);
      const lista = porAnio.get(anio) ?? [];
      lista.push(f);
      porAnio.set(anio, lista);
    }
  }

  return (
    <>
      <div className="encabezado">
        <h1>Calendario laboral</h1>
        <p>
          De aqui sale el reloj de todos los SLA. Un dia declarado aqui no cuenta para el
          plazo, igual que un sabado — y lo leen las dos implementaciones, la de Python y la
          del portal, para que no haya dos calendarios.
        </p>
      </div>

      {/* --- lo que es politica y vive en git --- */}
      <section className="rejilla">
        <div className="tarjeta">
          <div className="cifra">{politica.horasPorDia} h</div>
          <div className="etiqueta">Jornada</div>
          <p className="nota">Lo que dura un dia habil para el reloj.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{politica.diasHabiles.size}</div>
          <div className="etiqueta">Dias habiles</div>
          <p className="nota">
            {[...politica.diasHabiles].sort().map((d) => DIAS[d]).join(", ")}
          </p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{politica.offsetMs / 3_600_000}</div>
          <div className="etiqueta">Huso (UTC)</div>
          <p className="nota">Fijo: Mexico elimino el horario de verano en 2022.</p>
        </div>
        <div className="tarjeta">
          <div className="cifra">{festivos.ok ? festivos.datos.length : "—"}</div>
          <div className="etiqueta">Festivos declarados</div>
          <p className="nota">Se capturan aqui; el resto se cambia por PR.</p>
        </div>
      </section>

      <p className="nota" style={{ marginTop: 12 }}>
        La jornada, los dias habiles y el huso viven en{" "}
        <code>registry/policies/calendario-laboral.yaml</code> y se cambian por pull request:
        son mecanismo, y un horario que se edita desde una pantalla es un horario sin
        auditoria. Los festivos no — cambian cada año y son un dato de la empresa.
      </p>

      {/* --- los feriados, que son operacion --- */}
      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Dias festivos</h2>

      {!festivos.ok ? (
        <SinDatos
          motivo={festivos.motivo}
          detalle={festivos.detalle}
          queMostraria="los dias que no cuentan para el reloj del SLA, con quien los declaro y de donde salieron"
        />
      ) : (
        <>
          {festivos.datos.length === 0 ? (
            <div className="aviso">
              <strong>Ningun festivo declarado.</strong> Mientras la lista este vacia, el reloj
              del SLA trata todos los dias habiles por igual: un HITL de criticidad alta
              abierto el 15 de septiembre por la tarde vence el 16, que es feriado, cuando no
              hay nadie para atenderlo.
              <p className="nota" style={{ marginTop: 8 }}>
                Los dias del articulo 74 de la LFT son publicos, pero <strong>cuales descansa
                Fleeter de verdad</strong> —y si para operacion o solo administracion— es un
                dato que nadie ha confirmado. Por eso el sistema no los rellena solo: una lista
                inventada seria peor que ninguna, porque el calendario <em>se veria</em>
                calibrado.
              </p>
            </div>
          ) : (
            [...porAnio.entries()]
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([anio, lista]) => (
                <div key={anio} style={{ marginBottom: 18 }}>
                  <h3 style={{ fontSize: 15, marginBottom: 8 }}>
                    {anio} <span className="nota">· {lista.length} dia(s)</span>
                  </h3>
                  <div className="tarjeta desplaza">
                    <table>
                      <thead>
                        <tr>
                          <th>Fecha</th>
                          <th>Que se celebra</th>
                          <th>Alcance</th>
                          <th>Origen</th>
                          <th>Lo declaro</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {lista.map((f) => (
                          <tr key={f.fecha}>
                            <td>
                              <code>{f.fecha}</code>
                            </td>
                            <td>{f.motivo}</td>
                            <td>
                              {f.alcance === "completo" ? (
                                "no se trabaja"
                              ) : (
                                <span className="nota">solo administracion</span>
                              )}
                            </td>
                            <td className="nota">
                              {f.origen === "manual" ? "a mano" : f.origen === "ics" ? "importado" : "yaml"}
                            </td>
                            <td className="nota">{f.declarado_por_nombre ?? "—"}</td>
                            <td>
                              <Quitar fecha={f.fecha} puedeEditar={puedeEditar} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
          )}

          <div className="tarjeta" style={{ marginTop: 18 }}>
            <Editor puedeEditar={puedeEditar} />
          </div>
        </>
      )}

      <div className="aviso" style={{ marginTop: 24 }}>
        <strong>Importar, no sincronizar.</strong> El portal lee un <code>.ics</code> que tu
        subes; no se conecta a Outlook en vivo, y es deliberado. Este calendario decide cuando
        vencen las aprobaciones: si dependiera de un servicio externo, alguien moviendo un
        evento cambiaria en silencio cuando expira un HITL, y el dia que ese servicio no
        respondiera el SLA se quedaria sin saber que dia es habil. Importar es una decision que
        queda registrada con tu nombre; sincronizar seria una dependencia.
      </div>
    </>
  );
}
