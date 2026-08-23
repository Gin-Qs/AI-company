"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export interface Convocable {
  id: string;
  nombre: string;
  mision: string;
  tipo: "dominio" | "consultor";
}

/**
 * El formulario de convocatoria.
 *
 * Los tres campos son obligatorios y el boton se apaga sin ellos, pero eso es cortesia: la
 * regla de §5-bis.3.2 —«un encargo lleva que modulo, que problema y que restriccion»— la
 * aplica el servidor, y el servidor la aplica con el mismo codigo que el CLI. Un encargo
 * ambiguo no arranca; el agente pide contexto, no lo inventa.
 *
 * `faltantes` se pinta cuando el servidor rechaza: si dice que falta la descripcion, se ve
 * cual, no un «revisa el formulario».
 */
export function Formulario({ convocables }: { convocables: Convocable[] }) {
  const router = useRouter();
  const [agenteId, setAgenteId] = useState(convocables[0]?.id ?? "");
  const [titulo, setTitulo] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [entregable, setEntregable] = useState("");
  const [hitl, setHitl] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [faltantes, setFaltantes] = useState<string[]>([]);
  const [hecho, setHecho] = useState<{ id: string; traceId: string } | null>(null);

  if (convocables.length === 0) {
    return (
      <p className="nota">
        Hoy no puedes convocar a nadie. O ningun agente esta encendido, o los que lo estan no
        te tienen en su <code>invocable_por</code>. Se cambia en{" "}
        <code>registry/agents/*.yaml</code>, por PR.
      </p>
    );
  }

  const elegido = convocables.find((c) => c.id === agenteId);

  const convocar = async () => {
    setEnviando(true);
    setError(null);
    setFaltantes([]);
    try {
      const respuesta = await fetch("/api/encargos", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          agenteId,
          titulo,
          descripcion,
          entregableEsperado: entregable,
          hitl,
        }),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        setError(datos.error ?? "No se pudo convocar.");
        setFaltantes(datos.faltantes ?? []);
        return;
      }
      setHecho({ id: datos.id, traceId: datos.traceId });
      setTitulo("");
      setDescripcion("");
      setEntregable("");
      setHitl(false);
      router.refresh();
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setEnviando(false);
    }
  };

  const listo = titulo.trim() && descripcion.trim() && entregable.trim();

  return (
    <div className="formulario">
      {hecho && (
        <div className="aviso">
          <strong>{hecho.id} abierto.</strong> Su caso es <code>{hecho.traceId}</code>, y ahi
          queda toda su historia — quien lo convoco, cuando y cada paso que dé.
        </div>
      )}

      <label htmlFor="agente">A quien</label>
      <select
        id="agente"
        value={agenteId}
        onChange={(e) => setAgenteId(e.target.value)}
        disabled={enviando}
      >
        {convocables.map((c) => (
          <option key={c.id} value={c.id}>
            {c.id} — {c.nombre}
            {c.tipo === "consultor" ? " (consultor)" : ""}
          </option>
        ))}
      </select>
      {elegido?.mision && <p className="nota">{elegido.mision.slice(0, 220)}</p>}

      <label htmlFor="titulo">Titulo</label>
      <input
        id="titulo"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        placeholder="Una linea: que se necesita."
        disabled={enviando}
      />

      <label htmlFor="descripcion">Descripcion</label>
      <textarea
        id="descripcion"
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
        placeholder="Que modulo, que problema, que restriccion. Sin esto el agente no arranca."
        disabled={enviando}
      />

      <label htmlFor="entregable">Entregable esperado</label>
      <textarea
        id="entregable"
        value={entregable}
        onChange={(e) => setEntregable(e.target.value)}
        placeholder="Que tiene que existir cuando termine, y como se sabe que esta bien."
        disabled={enviando}
      />

      <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
        <input
          type="checkbox"
          checked={hitl}
          onChange={(e) => setHitl(e.target.checked)}
          disabled={enviando}
          style={{ width: "auto" }}
        />
        <span>
          Necesita firma humana.{" "}
          <span className="nota">
            Entra a la bandeja como caso critico: su SLA se cuenta en horas habiles, no en dias.
          </span>
        </span>
      </label>

      <div>
        <button type="button" onClick={convocar} disabled={enviando || !listo}>
          Convocar
        </button>
      </div>

      {error && (
        <div className="aviso">
          <strong className="alarma">No se convoco.</strong> {error}
          {faltantes.length > 0 && (
            <ul className="nota" style={{ marginTop: 8 }}>
              {faltantes.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
