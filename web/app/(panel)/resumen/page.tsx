import Link from "next/link";

import {
  consumoDelPeriodo,
  festivosDeclarados,
  hitlAbiertos,
  ultimaValidacion,
  umbralesPorCaso,
} from "@/lib/db/consultas";
import { bandejaDe, restanteLegible } from "@/lib/hitl";
import { cargarAgentes, panorama } from "@/lib/registro";
import { cargarCalendario } from "@/lib/registro/politicas";
import { sesion } from "@/lib/sesion";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";

// El registro se lee del sistema de archivos en cada peticion: es la fuente de verdad y
// cambia por despliegue, no en caliente.
export const dynamic = "force-dynamic";

const periodoDeHoy = (): string => new Date().toISOString().slice(0, 7);

export default async function Resumen() {
  const agentes = cargarAgentes();
  const p = panorama(agentes);
  const calendario = cargarCalendario();
  const periodo = periodoDeHoy();

  const s = await sesion();
  const [espera, umbrales, salud, consumo, festivos] = await Promise.all([
    hitlAbiertos(),
    umbralesPorCaso(),
    ultimaValidacion("main"),
    consumoDelPeriodo(periodo),
    festivosDeclarados(),
  ]);

  // Sin los festivos no se calcula el SLA: contarian los feriados como dias habiles y la
  // columna «vence» diria menos tiempo del que hay.
  const bandeja =
    espera.ok && festivos.ok && s.estado === "vinculada"
      ? bandejaDe({
          casos: espera.datos,
          persona: s.persona,
          registro: s.registro,
          umbrales: umbrales.ok
            ? Object.fromEntries(umbrales.datos.map((u) => [u.trace_id, u.umbral]))
            : {},
          festivos: festivos.datos.map((f) => f.fecha),
        })
      : [];

  return (
    <>
      <div className="encabezado">
        <h1>Resumen</h1>
        <p>
          Cuatro cosas, de cuatro fuentes distintas: el estado de los agentes sale de{" "}
          <code>registry/</code>; los HITL, el consumo y la salud del registro salen de
          Postgres. Cada bloque dice de donde viene lo suyo, y cuando no puede, lo dice
          tambien.
        </p>
      </div>

      {/* --- agentes: sale de git, siempre hay --- */}
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

      {/* Cuenta los del YAML y los declarados en la base: desde que existe la vista de
          calendario, los feriados son operacion y ya no se editan por PR. */}
      {festivos.ok && calendario.festivos.size + festivos.datos.length === 0 && (
        <div className="aviso">
          <strong>Calendario laboral sin calibrar.</strong> No hay ningun festivo declarado,
          asi que un HITL abierto la vispera de un feriado vencera ese mismo dia, cuando no
          haya nadie para atenderlo. Se declaran en <a href="/calendario">Calendario</a>.
          Jornada vigente: {calendario.horasPorDia} h, {calendario.diasHabiles.size} dias
          habiles.
          <p className="nota" style={{ marginTop: 8 }}>
            La lista esta vacia <strong>a proposito</strong>: los dias del articulo 74 de la
            LFT son publicos, pero cuales descansa Fleeter de verdad es un dato de la empresa
            que nadie ha confirmado. Una lista inventada seria peor que ninguna — el sistema
            se veria calibrado. Responsable: Nay. Decide: Gabriel.
          </p>
        </div>
      )}

      {/* --- HITL: lo que espera a una persona, lo mas cerca de vencer primero --- */}
      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Esperando a una persona</h2>
      {!espera.ok ? (
        <SinDatos
          motivo={espera.motivo}
          detalle={espera.detalle}
          queMostraria="los HITL abiertos, ordenados por el SLA que esta mas cerca de vencer"
        />
      ) : espera.datos.length === 0 ? (
        <VacioDeVerdad>
          Ningun caso espera a una persona. Es lo esperado hoy: los cinco agentes del MVP
          estan <code>listo</code> y sin encender, y su condicion de encendido es justamente
          esta bandeja.
        </VacioDeVerdad>
      ) : s.estado !== "vinculada" ? (
        <VacioDeVerdad>
          Hay {espera.datos.length} caso(s) esperando, y no se puede decir cuales te tocan sin
          saber quien eres en el registro.
        </VacioDeVerdad>
      ) : (
        <div className="tarjeta desplaza">
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>Agente</th>
                <th>Criticidad</th>
                <th>Responde</th>
                <th>Vence</th>
                <th>Puedes aprobarlo</th>
              </tr>
            </thead>
            <tbody>
              {bandeja.slice(0, 8).map((h) => (
                <tr key={h.caso.trace_id}>
                  <td>
                    <Link href={`/casos/${h.caso.trace_id}`}>
                      <code>{h.caso.trace_id}</code>
                    </Link>
                  </td>
                  <td>
                    <code>{h.agenteId}</code>
                  </td>
                  <td>{h.caso.criticidad}</td>
                  <td>{h.responsable ?? "sin declarar"}</td>
                  <td className={h.restanteMs < 0 ? "alarma" : undefined}>
                    {restanteLegible(h.restanteMs)}
                  </td>
                  <td className="nota">{h.decision.puede ? "si" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* --- salud del registro: el resumen; el detalle esta en su vista --- */}
      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Salud del registro</h2>
      {!salud.ok ? (
        <SinDatos
          motivo={salud.motivo}
          detalle={salud.detalle}
          queMostraria="el resultado de la ultima corrida de la CI sobre las reglas del registro"
        />
      ) : salud.datos === null ? (
        <VacioDeVerdad>
          La CI todavia no ha publicado ninguna corrida de <code>main</code>. La escribe{" "}
          <code>.github/workflows/validar.yml</code> y necesita el secreto{" "}
          <code>DIRECT_URL</code>.
        </VacioDeVerdad>
      ) : (
        <div className="tarjeta">
          <p style={{ margin: 0 }}>
            {salud.datos.en_verde} en verde,{" "}
            <span className={salud.datos.en_falla > 0 ? "alarma" : undefined}>
              {salud.datos.en_falla} en falla
            </span>
            , {salud.datos.omitidas} omitidas, {salud.datos.pendientes} pendientes.{" "}
            <Link href="/registro">Ver el detalle</Link>
          </p>
          <p className="nota" style={{ marginTop: 6 }}>
            Del commit <code>{salud.datos.commit_sha.slice(0, 8) || "sin declarar"}</code>,
            corrido el {new Date(salud.datos.corrido_en).toISOString().slice(0, 16).replace("T", " ")}{" "}
            UTC. No es en vivo, y por eso lleva fecha.
          </p>
        </div>
      )}

      {/* --- consumo: hoy sale vacio, y la pantalla explica por que --- */}
      <h2 style={{ marginTop: 34, marginBottom: 12 }}>Consumo de {periodo}</h2>
      {!consumo.ok ? (
        <SinDatos
          motivo={consumo.motivo}
          detalle={consumo.detalle}
          queMostraria="los tokens y el costo por agente del periodo, agregados desde los eventos"
        />
      ) : consumo.datos.length === 0 ? (
        <VacioDeVerdad>
          Cero consumo en {periodo}, y es correcto: ningun agente esta encendido, asi que no
          hay un solo paso con <code>tokens &gt; 0</code>. La vista de presupuesto completa es
          de la Fase C por esta razon — sus datos aparecen despues del primer agente encendido,
          y ese encendido depende de este portal.
        </VacioDeVerdad>
      ) : (
        <div className="tarjeta desplaza">
          <table>
            <thead>
              <tr>
                <th>Agente</th>
                <th>Pasos</th>
                <th>Tokens</th>
                <th>Costo MXN</th>
              </tr>
            </thead>
            <tbody>
              {consumo.datos.map((c) => (
                <tr key={c.actor}>
                  <td>
                    <code>{c.actor}</code>
                  </td>
                  <td>{c.pasos}</td>
                  <td>{c.tokens}</td>
                  {/* Cadena, nunca `number`: el importe no se convierte a float en el
                      camino a la pantalla (§8.3). */}
                  <td>{c.costo_mxn}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="nota" style={{ marginTop: 10 }}>
            Contra los topes de <code>budget.yaml</code>, que el propio archivo declara{" "}
            <code>calibrado: false</code>: son un punto de partida derivado del nivel de
            modelo, no de consumo observado. Por eso aqui no hay barras de porcentaje — una
            barra al 40% de un tope inventado se lee como autoridad.
          </p>
        </div>
      )}

      {/* --- lo que falta para encender: sale de git --- */}
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
