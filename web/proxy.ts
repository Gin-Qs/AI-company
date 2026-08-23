import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Solo monta el contexto de Clerk. La autorizacion NO se decide aqui.
 *
 * Hasta v7 se hacia con `createRouteMatcher`, que Clerk ya marca como obsoleto y con una
 * razon que conviene entender: un chequeo por patron de ruta puede DIVERGIR de como Next
 * enruta de verdad, y cuando diverge deja alcanzable justo lo que creias protegido. Lo
 * vimos en vivo: con el cache a medias, /resumen respondia 404 en vez de redirigir — el
 * middleware ya no reconocia una ruta que si existia.
 *
 * Asi que la puerta se pone donde estan los datos, no donde estan las URLs:
 * `app/(panel)/layout.tsx` llama a `auth.protect()` y todo lo que cuelga de el queda
 * cubierto por herencia, no por coincidencia de cadenas.
 */
export default clerkMiddleware();

export const config = {
  matcher: [
    // Todo menos los estaticos de Next y los archivos con extension.
    "/((?!_next|[^?]*\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/:path*",
  ],
};
