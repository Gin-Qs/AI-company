import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";

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
 */
export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  await auth.protect();

  return (
    <>
      <header className="barra">
        <span className="marca">Portal de mando</span>
        <nav>
          <Link href="/resumen">Resumen</Link>
          <Link href="/agentes">Agentes</Link>
        </nav>
        <UserButton />
      </header>
      <main>{children}</main>
    </>
  );
}
