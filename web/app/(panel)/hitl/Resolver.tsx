"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/**
 * Los dos botones de una decision, y el campo que la explica.
 *
 * Es un componente de cliente porque necesita estado (que se escribio, si esta enviando) y
 * porque el resultado tiene que aparecer sin recargar. Nada de lo que decide aqui protege
 * nada: `deshabilitado` pinta un boton apagado, y apagarlo es cortesia. Quien tenga las
 * herramientas del navegador puede mandar la peticion igual — y le va a responder 403 desde
 * `app/api/hitl/route.ts`, que es donde vive el control de verdad.
 *
 * `ultimoSeqVisto` viaja con la peticion: es el "yo vi este caso en este punto de su
 * historia". Sin el no hay candado (§8.4) y dos personas pueden sobrescribirse.
 */
export function Resolver({
  traceId,
  agenteId,
  umbral,
  ultimoSeqVisto,
  deshabilitado,
  motivoDelBloqueo,
}: {
  traceId: string;
  agenteId: string;
  umbral?: string;
  ultimoSeqVisto: number;
  deshabilitado: boolean;
  motivoDelBloqueo: string;
}) {
  const router = useRouter();
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hecho, setHecho] = useState<string | null>(null);

  if (deshabilitado) {
    return <p className="nota">{motivoDelBloqueo}</p>;
  }

  if (hecho) {
    return <p className="nota">{hecho}</p>;
  }

  const resolver = async (resolucion: "aprobar" | "rechazar") => {
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await fetch("/api/hitl", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ traceId, agenteId, resolucion, motivo, umbral, ultimoSeqVisto }),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        setError(datos.error ?? "No se pudo resolver.");
        // Un 409 significa que lo que tienes en pantalla ya no es lo que hay. Recargar los
        // datos del servidor es parte del mensaje, no una cortesia: seguir mirando la
        // version vieja es como se aprueba dos veces lo mismo.
        if (respuesta.status === 409) router.refresh();
        return;
      }
      setHecho(`Resuelto como ${datos.estado}, registrado a nombre de ${datos.decidio}.`);
      router.refresh();
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="resolver">
      <input
        type="text"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Por que. Queda en el registro con tu nombre."
        aria-label={`Motivo de la decision sobre ${traceId}`}
        disabled={enviando}
      />
      <button
        type="button"
        onClick={() => resolver("aprobar")}
        disabled={enviando || !motivo.trim()}
      >
        Aprobar
      </button>
      <button
        type="button"
        className="secundario"
        onClick={() => resolver("rechazar")}
        disabled={enviando || !motivo.trim()}
      >
        Rechazar
      </button>
      {error && <p className="nota alarma">{error}</p>}
    </div>
  );
}
