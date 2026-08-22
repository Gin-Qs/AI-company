# Umbrales del Gate de Autoridad

**Fuente de verdad ejecutable: [`registry/policies/authority-gate.yaml`](../registry/policies/authority-gate.yaml).**
Este documento explica el estado y el procedimiento de calibración; no duplica los valores.

## Estado: `calibrado: parcial`

**6 de 10 umbrales ya son reales.** Salen del organigrama firmado de Fleeter (junio 2026), no de
la arquitectura: pago a proveedor > $20K, descuento > 5%, plazo de pago > 45 días, firma de
contratos, SLA de CFDI a 24 h y fondo de emergencia de 3 meses. Todos escalan a Gabriel.

**Faltan tres**, y los tres tienen la misma causa:

> **Cotización** depende de margen objetivo y mínimo por ruta; **cobranza** de una política de
> días que no está documentada; **incidencia en ruta** de una tabla de severidad 1–5 que hay que
> acordar con Elias y Ana. El primero requiere costo por km real, que produce `svc-costing` —
> o sea la Fase 0. Calibrar antes de la Fase 0 es imposible; esperar a calibrar para empezar la
> Fase 0 es un bloqueo circular.

Esto es seguro porque **la Fase 0 no enciende ningún agente y no ejecuta ningún `ACT-*`**.
Ningún umbral se aplica a nada hasta la Fase 1.

## La tabla de precios ya es el gate

El hallazgo más útil de la calibración: el control determinístico de cotización **no hay que
inventarlo**. Gabriel ya fija tarifas y márgenes mínimos por ruta en una tabla pre-aprobada que
actualiza mensualmente, y Ana cotiza dentro de ella. Eso es exactamente un `CTL-LIMIT`
funcionando a mano.

`svc-pricing` **consume esa tabla como dato maestro**; no la sustituye ni la recalcula. Lo que
añade el sistema es: cargarla en `svc-masterdata`, versionarla, y contrastar el margen mínimo
declarado contra el margen real que `svc-profitability` mide después. Cuando esos dos números
discrepen, ahí está el valor.

## Procedimiento de calibración

Requisito de salida de la Fase 0. Sin esto, la Fase 1 no arranca.

1. `svc-profitability` entrega margen real por viaje, ruta, cliente y unidad sobre al menos un
   trimestre de histórico cargado por `svc-ingest`. Ya está construido:
   `python -m services.cli --datos data/real --json out/fase0.json` produce la distribución
   (`distribucion_margen`), el margen por ruta y las `desviaciones_tarifa` — ver
   [fase-0.md](fase-0.md).
2. `D2-03` (o el análisis humano equivalente, si D2-03 aún no existe) propone `margen_objetivo_pct`
   y `margen_minimo_pct` con la distribución real, no con un supuesto.

   > **Ojo con el círculo:** desde el cierre de la Fase 1, `D2-03` existe declarado pero
   > apagado, y una de sus condiciones de encendido es justamente que estos dos umbrales estén
   > calibrados. El paso 2 lo hace **una persona** con la salida de `svc-profitability`; el
   > agente entra después, a explicar y mantener lo que ya se calibró. Encenderlo para que
   > calibre su propia condición de encendido sería exactamente el bloqueo circular que este
   > documento evita en la Fase 0.
3. Dirección los autoriza. La autorización queda en `svc-runlog`.
4. Los umbrales de pago, descuento y cobranza se contrastan contra el histórico: si un umbral
   hubiera disparado HITL en más del ~20% de los casos, está mal puesto y genera fatiga de
   aprobación — que es el modo de falla que convierte el Gate en un sello automático.
5. Se sube `version`, se pone `calibrado: true` y se registra la fecha.

## Recalibración continua

§7.3 ya define la señal: **un caso que expira repetidamente es señal de un umbral mal calibrado.**
`svc-runlog` mide tasa de expiración y tasa de aprobación-sin-cambios por umbral. Un umbral que
se aprueba siempre sin modificación está puesto demasiado bajo y sólo produce fricción.
