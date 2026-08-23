import type { Motivo } from "@/lib/db/cliente";

/**
 * Lo que se pinta cuando una vista no pudo leer la base.
 *
 * Existe para que la respuesta a "¿por que esta vacio?" este en la pantalla y no en la
 * cabeza de quien la programo. Las alternativas —una tabla vacia, un cero, un esqueleto que
 * carga para siempre— se ven exactamente igual que un sistema sano sin nada que reportar.
 *
 * El titulo cambia con el motivo porque los tres mandan a hacer cosas distintas: uno a
 * configurar una variable, otro a RESTABLECER una contrasena que nadie perdio, el tercero a
 * leer un error de Postgres.
 */

const TITULO: Record<Motivo, string> = {
  sin_configurar: "Sin base de datos configurada",
  marcador: "Falta la contrasena de Postgres",
  error: "La base de datos respondio con un error",
};

export function SinDatos({
  motivo,
  detalle,
  queMostraria,
}: {
  motivo: Motivo;
  detalle: string;
  /** Que habria aqui si hubiera base. Sin esto, la pantalla no dice que se esta perdiendo. */
  queMostraria: string;
}) {
  return (
    <div className="aviso">
      <strong>{TITULO[motivo]}.</strong> {detalle}
      <p className="nota" style={{ marginTop: 10 }}>
        Esta vista mostraria {queMostraria}. No se pinta en ceros a proposito: unas cifras en
        cero se leen igual que un sistema sano que no tiene nada que reportar, y no es el caso.
      </p>
    </div>
  );
}

/**
 * El vacio legitimo: hay base, la consulta corrio y no devolvio nada.
 *
 * Es un estado distinto del de arriba y tiene que verse distinto. Confundirlos es lo que
 * hace que un portal diga "todo bien" cuando lo que pasa es que no se conecto.
 */
export function VacioDeVerdad({ children }: { children: React.ReactNode }) {
  return (
    <div className="tarjeta vacio">
      <p className="nota">{children}</p>
    </div>
  );
}
