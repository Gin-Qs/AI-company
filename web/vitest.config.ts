import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // A proposito NO es America/Mexico_City. El puerto del SLA tiene que dar el mismo
    // resultado corra donde corra: en Vercel (UTC) y en la maquina de quien programa.
    // Fijar aqui el huso a UTC hace que un getter local de Date que se cuele en el
    // codigo falle en las pruebas en vez de fallar en produccion.
    env: { TZ: "UTC" },
    include: ["lib/**/*.test.ts"],
  },
});
