import { redirect } from "next/navigation";

/**
 * La raiz no muestra nada: el portal empieza en el resumen, y esa ruta ya exige sesion
 * por el layout de (panel). Sin sesion, la cadena termina en /entrar.
 */
export default function Inicio() {
  redirect("/resumen");
}
