/**
 * Donde esta la raiz del repositorio, vista desde el portal.
 *
 * El portal vive en `web/` y lee archivos que estan un nivel arriba (`registry/`,
 * `office/`). Resolver esa ruta suena trivial y no lo es: el codigo corre en tres sitios
 * con reglas distintas —`next dev`, `vitest` y una funcion serverless de Vercel— y
 * `import.meta.url` no sobrevive igual a los tres empaquetados.
 *
 * Asi que no se adivina: se BUSCA. Se sube desde el directorio de trabajo hasta encontrar
 * `registry/policies/`, y si no aparece se falla con un mensaje que dice exactamente que
 * revisar. Un "archivo no encontrado" a secas, en produccion, cuesta una tarde.
 */

import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

/** Lo que tiene que existir para reconocer la raiz. */
const SEÑA = join("registry", "policies");

let memo: string | null = null;

export const raizDelRepo = (): string => {
  if (memo) return memo;

  let dir = process.cwd();
  for (let saltos = 0; saltos < 8; saltos += 1) {
    if (existsSync(join(/* turbopackIgnore: true */ dir, SEÑA))) {
      memo = dir;
      return dir;
    }
    const padre = dirname(dir);
    if (padre === dir) break; // llegamos a la raiz del disco
    dir = padre;
  }

  throw new Error(
    `No encuentro ${SEÑA} subiendo desde ${process.cwd()}. ` +
      `En Vercel esto significa que next.config.ts no esta incluyendo ../registry/** con ` +
      `outputFileTracingIncludes: el portal lee el registro desde el sistema de archivos, ` +
      `y con root directory = web/ esos archivos no entran al bundle por defecto.`,
  );
};

/**
 * Une una ruta relativa a la raiz del repositorio.
 *
 * `turbopackIgnore` desactiva el analisis estatico de esta llamada. Sin el, Next ve un
 * `join()` con segmentos variables, no puede saber que archivos hacen falta, y por si
 * acaso EMPAQUETA EL PROYECTO ENTERO —incluido todo el codigo Python y `public/`—. Eso
 * infla el despliegue y puede reventar el limite de tamaño de una funcion.
 *
 * Desactivarlo es seguro aqui, y solo aqui, porque los archivos que de verdad se leen
 * estan declarados uno por uno en `outputFileTracingIncludes` de `next.config.ts`. Si
 * algun dia se lee un archivo nuevo del registro, hay que agregarlo alli: el rastreo
 * automatico ya no lo va a encontrar solo.
 */
export const desdeRaiz = (...partes: string[]): string =>
  join(/* turbopackIgnore: true */ raizDelRepo(), ...partes);
