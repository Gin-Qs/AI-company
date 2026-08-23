"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/**
 * Pausar la oficina, o levantarla. Los dos exigen que se escriba algo, y no por formalismo.
 *
 * Una pausa sin condicion de reanudacion es una pausa que nadie sabe cuando termina, y se
 * levanta el dia que a alguien le urge algo. Un levantamiento sin motivo deja la pregunta
 * "¿se cumplio la condicion o hacia falta trabajar?" sin respuesta para siempre.
 *
 * El boton apagado es cortesia. El control esta en `app/api/oficina/pausa/route.ts`, que
 * comprueba el rol contra el registro y rechaza con 403 a quien no sea Direccion — venga la
 * peticion de este formulario o de la consola del navegador.
 */
export function Controles({ pausada, esDireccion }: { pausada: boolean; esDireccion: boolean }) {
  const router = useRouter();
  const [motivo, setMotivo] = useState("");
  const [condicion, setCondicion] = useState("");
  const [porque, setPorque] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!esDireccion) {
    return (
      <p className="nota">
        Pausar y reanudar la oficina es de Direccion. El rol sale de{" "}
        <code>authority-gate.yaml → autoridades.direccion</code> y se deriva en cada peticion:
        si cambia ahi, cambia aqui.
      </p>
    );
  }

  const mandar = async (cuerpo: Record<string, string>) => {
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await fetch("/api/oficina/pausa", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(cuerpo),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        setError(datos.error ?? "No se pudo.");
        return;
      }
      setMotivo("");
      setCondicion("");
      setPorque("");
      router.refresh();
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setEnviando(false);
    }
  };

  if (pausada) {
    return (
      <div className="formulario">
        <label htmlFor="porque">Por que se reanuda</label>
        <textarea
          id="porque"
          value={porque}
          onChange={(e) => setPorque(e.target.value)}
          placeholder="Se cumplio la condicion, y asi: ..."
          disabled={enviando}
        />
        <div>
          <button
            type="button"
            onClick={() => mandar({ accion: "reanudar", porque })}
            disabled={enviando || !porque.trim()}
          >
            Reanudar la oficina
          </button>
        </div>
        {error && <p className="nota alarma">{error}</p>}
      </div>
    );
  }

  return (
    <div className="formulario">
      <label htmlFor="motivo">Motivo de la pausa</label>
      <textarea
        id="motivo"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Que hace necesario detener toda convocatoria."
        disabled={enviando}
      />
      <label htmlFor="condicion">Se reanuda cuando</label>
      <textarea
        id="condicion"
        value={condicion}
        onChange={(e) => setCondicion(e.target.value)}
        placeholder="Que tiene que pasar para volver a trabajar. Sin esto no se puede pausar."
        disabled={enviando}
      />
      <div>
        <button
          type="button"
          className="secundario"
          onClick={() => mandar({ accion: "pausar", motivo, seReanudaCuando: condicion })}
          disabled={enviando || !motivo.trim() || !condicion.trim()}
        >
          Pausar la oficina
        </button>
      </div>
      {error && <p className="nota alarma">{error}</p>}
    </div>
  );
}
