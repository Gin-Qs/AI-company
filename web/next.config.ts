import { resolve } from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // EL AJUSTE QUE NO SE PUEDE OLVIDAR.
  //
  // El portal lee el registro desde el sistema de archivos (registry/, office/), y esos
  // archivos viven UN NIVEL ARRIBA de este proyecto. En Vercel el root directory es `web/`,
  // asi que por defecto no entran al bundle: la app compila, despliega, y falla en la
  // primera peticion con "archivo no encontrado".
  //
  // Se incluyen explicitamente. Solo lectura: el portal nunca escribe en registry/.
  // Absoluto a proposito: Next avisa si es relativo, porque el directorio de trabajo
  // no es el mismo en `next build` local y en el contenedor de Vercel.
  outputFileTracingRoot: resolve(process.cwd(), ".."),
  outputFileTracingIncludes: {
    "/**": [
      "../registry/agents/**",
      "../registry/consultants/**",
      "../registry/teams/**",
      "../registry/policies/**",
      "../office/identidades.yaml",
    ],
  },
};

export default nextConfig;
