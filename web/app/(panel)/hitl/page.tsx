import Link from "next/link";

import { hitlAbiertos, umbralesPorCaso, type Caso } from "@/lib/db/consultas";
import { bandejaDe, restanteLegible } from "@/lib/hitl";
import { sesion } from "@/lib/sesion";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";
import { Resolver } from "./Resolver";

export const dynamic = "force-dynamic";

/**
 * La bandeja unica de HITL (vista 4). El punto del ejercicio.
 *
 * Doce encargos abiertos la estan construyendo, cinco agentes la declaran como condicion de
 * encendido en su propio registro, y mientras no exista `agents/runtime.py` seguira
 * rechazando la convocatoria nombrandola. Esto no habilita un tablero: es el encendido.
 *
 * Ordena por SLA restante, no por fecha de creacion. Una bandeja ordenada por antigüedad
 * entierra lo que urge debajo de lo que llego primero.
 */
export default async function Bandeja({
  searchParams,
}: {
  searchParams: Promise<{ todos?: string }>;
}) {
  const { todos } = await searchParams;
  const verTodos = todos === "1";

  const s = await sesion();
  const [espera, umbrales] = await Promise.all([hitlAbiertos(), umbralesPorCaso()]);

  return (
    <>
      <div className="encabezado">
        <h1>Bandeja de HITL</h1>
        <p>
          Lo que espera a una persona, ordenado por lo que menos tiempo le queda. El SLA se
          cuenta en <strong>horas habiles</strong> segun{" "}
          <code>registry/policies/calendario-laboral.yaml</code>, no en horas de reloj: un
          caso que entra el viernes por la tarde no vence el sabado.
        </p>
      </div>

      {!espera.ok ? (
        <SinDatos
          motivo={espera.motivo}
          detalle={espera.detalle}
          queMostraria="los casos que esperan a una persona, con su SLA, el umbral que disparo el gate y quien puede aprobarlos"
        />
      ) : s.estado !== "vinculada" ? (
        <VacioDeVerdad>
          Hay {espera.datos.length} caso(s) esperando. No se pueden mostrar sin saber quien
          eres en el registro: de ahi sale que te toca ver y que puedes aprobar. Aprobar sin
          eso dejaria un evento sin autor, que es exactamente el hueco que esta bandeja
          existe para cerrar.
        </VacioDeVerdad>
      ) : (
        <BandejaResuelta
          casos={espera.datos}
          umbrales={
            umbrales.ok ? Object.fromEntries(umbrales.datos.map((u) => [u.trace_id, u.umbral])) : {}
          }
          sesion={s}
          verTodos={verTodos}
        />
      )}
    </>
  );
}

function BandejaResuelta({
  casos,
  umbrales,
  sesion: s,
  verTodos,
}: {
  casos: Caso[];
  umbrales: Record<string, string>;
  sesion: Extract<Awaited<ReturnType<typeof sesion>>, { estado: "vinculada" }>;
  verTodos: boolean;
}) {
  const bandeja = bandejaDe({
    casos,
    persona: s.persona,
    registro: s.registro,
    umbrales,
    soloLosSuyos: !verTodos,
  });
  const total = casos.length;

  if (total === 0) {
    return (
      <VacioDeVerdad>
        Ningun caso espera a una persona. Es lo esperado hoy: los cinco agentes del MVP estan{" "}
        <code>listo</code> y sin encender, y su condicion de encendido es justamente esta
        bandeja.
      </VacioDeVerdad>
    );
  }

  return (
    <>
      <p className="nota" style={{ marginBottom: 14 }}>
        {verTodos ? (
          <>
            Viendo los {total} casos abiertos.{" "}
            <Link href="/hitl">Ver solo los tuyos</Link>
          </>
        ) : (
          <>
            {bandeja.length} de {total} casos abiertos te llegan a ti.{" "}
            {/* Que existan otros se dice, aunque no se puedan tocar. Una bandeja que
                esconde el resto se lee como "no hay nada mas". */}
            <Link href="/hitl?todos=1">Ver todos</Link>
          </>
        )}
      </p>

      {bandeja.length === 0 ? (
        <VacioDeVerdad>
          Ninguno de los {total} casos abiertos te llega a ti. Los equipos donde respondes o
          apoyas no tienen nada esperando.
        </VacioDeVerdad>
      ) : (
        <div className="tarjeta desplaza">
          <table>
            <thead>
              <tr>
                <th>Caso</th>
                <th>Agente</th>
                <th>Umbral</th>
                <th>Responde</th>
                <th>SLA</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {bandeja.map((h) => (
                <tr key={h.caso.trace_id}>
                  <td>
                    <Link href={`/casos/${h.caso.trace_id}`}>
                      <code>{h.caso.trace_id}</code>
                    </Link>
                    <div className="nota">
                      {h.caso.tipo} · {h.caso.referencia} · criticidad {h.caso.criticidad}
                    </div>
                  </td>
                  <td>
                    <code>{h.agenteId}</code>
                  </td>
                  <td>
                    {h.umbral ? (
                      <code>{h.umbral}</code>
                    ) : (
                      // Sin umbral declarado, la politica `co_owners_con_autoridad` no puede
                      // conceder nada. No es un hueco de la pantalla: no se aprueba lo que no
                      // se sabe que es.
                      <span className="nota">sin declarar</span>
                    )}
                  </td>
                  <td>{h.responsable ?? <span className="nota">sin declarar</span>}</td>
                  <td className={h.restanteMs < 0 ? "alarma" : undefined}>
                    {restanteLegible(h.restanteMs)}
                    {h.alVencer && (
                      <div className="nota alarma">
                        {/* Ninguna accion al vencer es "aprobar", ni con cero escalamientos
                            ni con dos. El tipo `Accion` ni siquiera la contiene. */}
                        al vencer: {h.alVencer.accion}
                      </div>
                    )}
                  </td>
                  <td>
                    <Resolver
                      traceId={h.caso.trace_id}
                      agenteId={h.agenteId}
                      umbral={h.umbral}
                      ultimoSeqVisto={h.caso.ultimo_seq}
                      deshabilitado={!h.decision.puede}
                      motivoDelBloqueo={h.decision.motivo}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="aviso" style={{ marginTop: 24 }}>
        <strong>Aprobar entrega; rechazar bloquea.</strong> Rechazar no expira el caso, y la
        diferencia importa: expirar es lo que le pasa a un caso que nadie miro. Confundir
        &laquo;lo revise y dije que no&raquo; con &laquo;se me paso&raquo; borraria la
        distincion entre una decision y un descuido, que es justo la que esta bandeja existe
        para crear.
      </div>
    </>
  );
}
