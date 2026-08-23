"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { leerIcs, type EventoIcs } from "@/lib/ics";

type Alcance = "completo" | "administrativo";

/**
 * Declarar feriados a mano o importarlos de un `.ics`.
 *
 * EL ARCHIVO SE LEE EN EL NAVEGADOR ANTES DE MANDARLO. No es una optimizacion: permite
 * enseñar exactamente que dias van a entrar y cuales se van a ignorar **antes** de tocar la
 * base. Una importacion que solo se puede revisar despues es una importacion que se revisa
 * cuando ya se rompio algo.
 *
 * El mismo parser corre en los dos lados —aqui para la vista previa y en la ruta para
 * escribir—, asi que lo que se ve es lo que se guarda. El servidor no confia en la vista
 * previa: vuelve a leer el archivo entero.
 */
export function Editor({ puedeEditar }: { puedeEditar: boolean }) {
  const router = useRouter();
  const archivoRef = useRef<HTMLInputElement>(null);

  const [fecha, setFecha] = useState("");
  const [motivo, setMotivo] = useState("");
  const [alcance, setAlcance] = useState<Alcance>("completo");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const [previa, setPrevia] = useState<{
    nombre: string;
    ics: string;
    eventos: EventoIcs[];
    omitidos: string[];
  } | null>(null);

  if (!puedeEditar) {
    return (
      <p className="nota">
        El calendario laboral decide cuando vencen las aprobaciones, asi que lo declara quien
        responde por la operacion. Tu rol se deriva de{" "}
        <code>registry/policies/authority-gate.yaml</code> en cada peticion.
      </p>
    );
  }

  const mandar = async (cuerpo: Record<string, unknown>, alTerminar?: () => void) => {
    setEnviando(true);
    setError(null);
    setAviso(null);
    try {
      const respuesta = await fetch("/api/festivos", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(cuerpo),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        setError(datos.error ?? "No se pudo.");
        return;
      }
      alTerminar?.();
      router.refresh();
      return datos;
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setEnviando(false);
    }
  };

  const elegirArchivo = async (archivo: File | undefined) => {
    setError(null);
    setAviso(null);
    if (!archivo) return setPrevia(null);
    const ics = await archivo.text();
    const { eventos, omitidos } = leerIcs(ics);
    setPrevia({ nombre: archivo.name, ics, eventos, omitidos });
  };

  const importar = async () => {
    if (!previa) return;
    const datos = await mandar({ accion: "importar", ics: previa.ics, alcance });
    if (!datos) return;
    const partes = [`${datos.agregados} nuevos`, `${datos.actualizados} actualizados`];
    if (datos.respetados?.length) {
      partes.push(`${datos.respetados.length} respetados por estar declarados a mano`);
    }
    setAviso(`Importado de ${previa.nombre}: ${partes.join(", ")}.`);
    setPrevia(null);
    if (archivoRef.current) archivoRef.current.value = "";
  };

  return (
    <>
      <div className="formulario">
        <h3 style={{ margin: 0, fontSize: 15 }}>Declarar un dia</h3>

        <label htmlFor="fecha">Fecha</label>
        <input
          id="fecha"
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          disabled={enviando}
        />

        <label htmlFor="motivo">Que se celebra</label>
        <input
          id="motivo"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          placeholder="Dia de la Independencia"
          disabled={enviando}
        />

        <label htmlFor="alcance">Alcance</label>
        <select
          id="alcance"
          value={alcance}
          onChange={(e) => setAlcance(e.target.value as Alcance)}
          disabled={enviando}
        >
          <option value="completo">Completo — no se trabaja</option>
          <option value="administrativo">Administrativo — operacion sigue</option>
        </select>

        <div>
          <button
            type="button"
            onClick={() =>
              mandar({ accion: "declarar", fecha, motivo, alcance }, () => {
                setFecha("");
                setMotivo("");
                setAviso("Dia declarado.");
              })
            }
            disabled={enviando || !fecha || !motivo.trim()}
          >
            Declarar
          </button>
        </div>
      </div>

      <hr style={{ border: 0, borderTop: "1px solid var(--borde)", margin: "22px 0" }} />

      <div className="formulario">
        <h3 style={{ margin: 0, fontSize: 15 }}>Importar de un calendario</h3>
        <p className="nota" style={{ margin: 0 }}>
          En Outlook: <em>Calendario &rarr; Compartir &rarr; Guardar calendario</em>, o desde
          Outlook web <em>Configuracion &rarr; Calendario &rarr; Calendarios compartidos &rarr;
          Publicar</em>, y descarga el <code>.ics</code>. Entran solo los eventos de{" "}
          <strong>dia completo</strong>: un feriado es un dia entero, y una junta de las 3 no
          deberia volver inhabil ese dia.
        </p>

        <input
          ref={archivoRef}
          type="file"
          accept=".ics,text/calendar"
          onChange={(e) => elegirArchivo(e.target.files?.[0])}
          disabled={enviando}
        />

        {previa && (
          <div className="tarjeta" style={{ background: "var(--fondo)" }}>
            <p style={{ margin: 0, fontWeight: 600 }}>
              {previa.eventos.length} dia(s) entrarian de {previa.nombre}
            </p>
            {previa.eventos.length > 0 && (
              <ul className="nota" style={{ marginTop: 8 }}>
                {previa.eventos.slice(0, 12).map((e) => (
                  <li key={e.fecha}>
                    <code>{e.fecha}</code> — {e.motivo}
                  </li>
                ))}
                {previa.eventos.length > 12 && <li>… y {previa.eventos.length - 12} mas</li>}
              </ul>
            )}
            {/* Lo que se deja fuera se enseña. Un import que no dice lo que ignoro se lee
                como uno que lo trajo todo. */}
            {previa.omitidos.length > 0 && (
              <>
                <p className="nota" style={{ marginTop: 10, fontWeight: 600 }}>
                  Se ignoran {previa.omitidos.length}:
                </p>
                <ul className="nota">
                  {previa.omitidos.slice(0, 8).map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="nota" style={{ marginTop: 10 }}>
              Los dias que ya declaraste <strong>a mano</strong> no se tocan: el archivo no
              sabe cuales descansa Fleeter de verdad, y tu si.
            </p>
            <div style={{ marginTop: 12 }}>
              <button
                type="button"
                onClick={importar}
                disabled={enviando || previa.eventos.length === 0}
              >
                Importar {previa.eventos.length} dia(s)
              </button>
            </div>
          </div>
        )}
      </div>

      {aviso && <p className="nota" style={{ marginTop: 14 }}>{aviso}</p>}
      {error && (
        <div className="aviso" style={{ marginTop: 14 }}>
          <strong className="alarma">No se guardo.</strong> {error}
        </div>
      )}
    </>
  );
}

/** El boton de quitar, aparte para poder ponerlo en cada fila de la tabla. */
export function Quitar({ fecha, puedeEditar }: { fecha: string; puedeEditar: boolean }) {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);
  if (!puedeEditar) return null;

  return (
    <button
      type="button"
      className="secundario"
      disabled={enviando}
      onClick={async () => {
        setEnviando(true);
        await fetch("/api/festivos", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ accion: "borrar", fecha }),
        });
        router.refresh();
        setEnviando(false);
      }}
    >
      Quitar
    </button>
  );
}
