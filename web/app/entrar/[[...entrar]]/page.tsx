import { SignIn } from "@clerk/nextjs";

/**
 * La unica ruta publica del portal.
 *
 * No hay pagina de registro y no es un olvido: nadie se registra solo. A cada persona la
 * invita un admin desde Clerk, y su nombre tiene que existir ademas en
 * registry/policies/authority-gate.yaml. Autenticado no es autorizado.
 */
export default function Entrar() {
  return (
    <div className="centrado">
      <SignIn />
    </div>
  );
}
