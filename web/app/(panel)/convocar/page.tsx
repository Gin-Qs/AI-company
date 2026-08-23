import { convocablesPor } from "@/lib/convocar";
import { pausaActiva } from "@/lib/db/consultas";
import { sesion } from "@/lib/sesion";

import { SinDatos, VacioDeVerdad } from "../_componentes/SinDatos";
import { Formulario } from "./Formulario";

export const dynamic = "force-dynamic";

/**
 * Convocar agente (vista 8). Envuelve las reglas de `agents/runtime.py:convocar()`.
 *
 * La pantalla ofrece solo lo que la persona puede convocar de verdad — una lista que
 * incluyera lo que el servidor va a rechazar entrena a la gente a ignorar los errores— pero
 * el veredicto final lo da el servidor con el mismo codigo que el CLI, contrastado contra el
 * Python con vectores dorados (`tests/fixtures/convocatoria-vectores.json`).
 */
export default async function Convocar() {
  const s = await sesion();
  const pausa = await pausaActiva();

  if (s.estado !== "vinculada") {
    return (
      <>
        <div className="encabezado">
          <h1>Convocar agente</h1>
        </div>
        <VacioDeVerdad>
          Convocar escribe un encargo a tu nombre, y no se puede sin saber quien eres en el
          registro. Un encargo sin autor real es exactamente el hueco que este portal existe
          para cerrar.
        </VacioDeVerdad>
      </>
    );
  }

  const convocables = convocablesPor(s.persona, s.registro).map((a) => ({
    id: a.id,
    nombre: a.nombre,
    mision: a.mision,
    tipo: a.tipo,
  }));

  return (
    <>
      <div className="encabezado">
        <h1>Convocar agente</h1>
        <p>
          Abre un encargo con todas las reglas aplicadas: la pausa de la oficina, el estado
          del agente, quien puede convocarlo y que el encargo no sea ambiguo. Son las mismas
          reglas que aplica <code>agents/runtime.py</code> — no una version parecida.
        </p>
      </div>

      {/* La pausa se enseña ANTES del formulario. Dejar escribir un encargo entero para
          rechazarlo al enviar es hacerle perder el tiempo a quien ya no podia convocar. */}
      {!pausa.ok ? (
        <SinDatos
          motivo={pausa.motivo}
          detalle={pausa.detalle}
          queMostraria="si la oficina esta en pausa, que es lo primero que decide si se puede convocar"
        />
      ) : pausa.datos.activa ? (
        <div className="aviso">
          <strong>La oficina esta en pausa.</strong> Desde {pausa.datos.desde?.slice(0, 16).replace("T", " ")} UTC,
          por {pausa.datos.por}: {pausa.datos.motivo}
          <p className="nota" style={{ marginTop: 8 }}>
            <strong>Se reanuda cuando:</strong> {pausa.datos.seReanudaCuando}
          </p>
          <p className="nota" style={{ marginTop: 8 }}>
            Mientras siga activa, el runtime rechaza toda convocatoria — desde aqui y desde el
            CLI, porque los dos leen la misma fila. Lo que ya esta abierto no se cierra ni se
            pierde. Se levanta en <a href="/oficina">Oficina</a>, y solo Direccion.
          </p>
        </div>
      ) : null}

      <div className="tarjeta">
        <Formulario convocables={convocables} />
      </div>

      <div className="aviso" style={{ marginTop: 24 }}>
        <strong>Convocar no enciende a nadie.</strong> De los diecisiete agentes del registro
        solo se pueden convocar los que estan <code>built</code>. Los cinco del MVP siguen{" "}
        <code>listo</code>: su contrato esta completo y les faltan condiciones de encendido con
        dueño, que se ven en <a href="/resumen">Resumen</a>. Subir un estado a mano no es una
        opcion de esta pantalla — se hace por PR, cerrando lo que el estado promete.
      </div>
    </>
  );
}
