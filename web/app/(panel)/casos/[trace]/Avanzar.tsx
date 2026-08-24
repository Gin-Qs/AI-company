"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Lo que se puede hacer desde cada estado, con el nombre que usa quien trabaja. */
const DESDE: Record<string, Array<{ avance: string; boton: string; pista: string }>> = {
  recibido: [
    { avance: "empezar", boton: "Empezar", pista: "El agente arranca: el caso pasa a en proceso." },
    { avance: "bloquear", boton: "Bloquear", pista: "Falta contexto y nadie puede avanzar." },
  ],
  en_proceso: [
    { avance: "mandar_a_firma", boton: "Mandar a firma", pista: "Va a la bandeja y empieza a correr su SLA." },
    { avance: "bloquear", boton: "Bloquear", pista: "Falta contexto y nadie puede avanzar." },
  ],
  esperando_validacion: [
    { avance: "mandar_a_firma", boton: "Mandar a firma", pista: "Va a la bandeja y empieza a correr su SLA." },
    { avance: "bloquear", boton: "Bloquear", pista: "Falta contexto y nadie puede avanzar." },
  ],
  esperando_humano: [
    { avance: "bloquear", boton: "Bloquear", pista: "Sacarlo de la bandeja: falta algo para poder decidir." },
  ],
  bloqueado: [
    { avance: "desbloquear", boton: "Desbloquear", pista: "Ya hay contexto: vuelve a en proceso." },
  ],
};

/**
 * Mover el caso por la maquina de estados.
 *
 * NO hay boton para cerrar. Un caso se entrega desde la bandeja, con la firma de quien tiene
 * autoridad — si se pudiera cerrar desde aqui, el Gate seria opcional y la bandeja
 * decorativa. `esperando_humano` sale de esta pantalla por una sola puerta: bloquearlo
 * porque falta algo. Aprobar y rechazar viven donde vive la autoridad.
 */
export function Avanzar({
  traceId,
  agenteId,
  estado,
  ultimoSeqVisto,
}: {
  traceId: string;
  agenteId: string;
  estado: string;
  ultimoSeqVisto: number;
}) {
  const router = useRouter();
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const opciones = DESDE[estado] ?? [];

  if (opciones.length === 0) {
    return (
      <p className="nota">
        {estado === "entregado" || estado === "expirado"
          ? "El caso cerro. Su historia sigue consultable; su estado ya no se mueve."
          : `Desde ${estado.replace(/_/g, " ")} no hay movimiento disponible.`}
      </p>
    );
  }

  const mover = async (avance: string) => {
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await fetch("/api/casos", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ traceId, agenteId, avance, motivo, ultimoSeqVisto }),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        setError(datos.error ?? "No se pudo mover el caso.");
        // Un 409 significa que lo que ves ya no es lo que hay.
        if (respuesta.status === 409) router.refresh();
        return;
      }
      setMotivo("");
      router.refresh();
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="formulario">
      <label htmlFor="motivo-avance">Por que</label>
      <input
        id="motivo-avance"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Queda en el registro con tu nombre."
        disabled={enviando}
      />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {opciones.map((o) => (
          <button
            key={o.avance}
            type="button"
            className={o.avance === "bloquear" ? "secundario" : undefined}
            onClick={() => mover(o.avance)}
            disabled={enviando || !motivo.trim()}
            title={o.pista}
          >
            {o.boton}
          </button>
        ))}
      </div>
      <p className="nota" style={{ margin: 0 }}>
        {opciones.map((o) => o.pista).join(" ")}
      </p>
      {error && (
        <div className="aviso">
          <strong className="alarma">No se movio.</strong> {error}
        </div>
      )}
    </div>
  );
}
