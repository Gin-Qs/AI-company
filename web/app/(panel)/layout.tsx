import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";

import { sesion } from "@/lib/sesion";

/**
 * El marco del portal, y su puerta.
 *
 * `auth.protect()` va AQUI y no en el middleware: protege por herencia de arbol, no por
 * coincidencia de rutas. Cualquier pagina que alguien agregue bajo `(panel)/` nace
 * protegida sin que haya que acordarse de nada — que es la unica clase de control que
 * sobrevive a un equipo con prisa.
 *
 * En Next 15+ `auth()` es asincrona. Sin sesion, redirige a /entrar.
 *
 * No hay boton de registro, solo el de la sesion activa: el portal es invite-only.
 *
 * LA SEGUNDA PUERTA (§7.4). Estar autenticado no es estar autorizado. Despues de Clerk viene
 * la fila de `personas`, y si la base responde que no existe, la persona no pasa de aqui.
 * Es una pantalla, no un 403 a secas: quien llega asi tiene una cuenta legitima y necesita
 * saber que le falta y a quien pedirselo.
 */
export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  await auth.protect();
  const s = await sesion();

  if (s.estado === "no_vinculada") {
    return (
      <main className="centrado">
        <div className="tarjeta" style={{ maxWidth: 560 }}>
          <h1 style={{ marginTop: 0 }}>Tu cuenta existe. Tu autoridad, no.</h1>
          <p className="nota">
            Iniciaste sesion como <strong>{s.cuenta}</strong>. {s.motivo}
          </p>
          <p className="nota">
            No es un error tuyo ni algo que puedas arreglar desde aqui. El nombre tiene que
            existir en <code>registry/policies/authority-gate.yaml</code> y tener su fila en{" "}
            <code>personas</code>: de ahi sale quien responde por que equipo y quien puede
            aprobar que umbral. Sin esa fila, el portal no sabria a nombre de quien registrar
            lo que hagas — y un evento sin autor real es justo el hueco que este portal existe
            para cerrar.
          </p>
          <p style={{ marginTop: 18 }}>
            <UserButton />
          </p>
        </div>
      </main>
    );
  }

  return (
    <>
      <header className="barra">
        <span className="marca">Portal de mando</span>
        <nav>
          <Link href="/resumen">Resumen</Link>
          <Link href="/agentes">Agentes</Link>
          <Link href="/hitl">Bandeja</Link>
          <Link href="/convocar">Convocar</Link>
          <Link href="/casos">Casos</Link>
          <Link href="/oficina">Oficina</Link>
          <Link href="/calendario">Calendario</Link>
          <Link href="/registro">Salud del registro</Link>
        </nav>
        {s.estado === "vinculada" && (
          <span className="quien" title={`Rol derivado del registro: ${s.persona.rol}`}>
            {s.persona.nombre} <span className="nota">· {s.persona.rol}</span>
          </span>
        )}
        <UserButton />
      </header>
      <main>
        {/* Se ve en TODAS las paginas, no solo en la que fallo. Que el portal se pueda leer
            sin base es una concesion; que se pueda leer sin decir que esta a medias, no. */}
        {s.estado === "sin_verificar" && (
          <div className="aviso">
            <strong>Sesion sin verificar contra el registro.</strong> Entraste como{" "}
            <strong>{s.cuenta}</strong>, pero no se pudo comprobar a que persona del registro
            corresponde: {s.detalle}
            <p className="nota" style={{ marginTop: 10 }}>
              Las vistas de lectura funcionan —el registro vive en git, no en la base—. Lo que
              no se puede hacer sin esto es <strong>actuar</strong>: aprobar un HITL, convocar
              a un agente o pausar la oficina quedarian registrados sin autor, y un evento sin
              autor no es auditable.
            </p>
          </div>
        )}
        {children}
      </main>
    </>
  );
}
