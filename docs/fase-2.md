# Fase 2 — Cerrar el ciclo operación → ingreso

**Preparada, no construida.** Cinco servicios y dos agentes declarados en el registro; cero
líneas de código nuevas y cero agentes encendidos.

Preparar una fase aquí significa una cosa concreta: **escribir qué va a hacer cada pieza, qué
pruebas la van a aceptar y qué decisiones faltan, antes de construirla.** Un contrato escrito
después del código es una descripción; escrito antes es un criterio.

| Pieza | Contrato | Qué resuelve |
|---|---|---|
| `svc-doc-checklist` | [yaml](../registry/services/svc-doc-checklist.yaml) | Si el expediente del viaje está completo |
| `svc-invoicing` | [yaml](../registry/services/svc-invoicing.yaml) | El comprobante y su timbrado |
| `svc-cfdi-validate` | [yaml](../registry/services/svc-cfdi-validate.yaml) | Si el CFDI y la Carta Porte cumplen |
| `svc-ar` | [yaml](../registry/services/svc-ar.yaml) | Cartera, prioridad de cobranza y flujo esperado |
| `svc-notify` | [yaml](../registry/services/svc-notify.yaml) | Avisos por plantilla fija, sin LLM |
| `D3-05` Evidencias y Cierre | [yaml](../registry/agents/D3-05-evidencias-y-cierre-de-viaje.yaml) | Persigue el documento que falta |
| `D2-04` Ciclo de Ingreso | [yaml](../registry/agents/D2-04-ciclo-de-ingreso.yaml) | Prepara la factura y sigue la cobranza |

## Qué agujero tapa

La v1 tenía dieciséis agentes de operación y ninguno que cerrara el ciclo: la empresa movía
carga, cerraba viajes y **facturaba a mano**. El hueco no era de inteligencia, era de proceso —
por eso `D2-04` aparece en la arquitectura marcado como *hueco de facturación* y no como
absorción de un agente de la v1.

El ciclo completo es: viaje cerrado → expediente completo → comprobante → validación → timbrado
→ cartera → cobro. La Fase 0 dejó el costo, la Fase 1 dejó el precio; **esta fase es la que
convierte el precio en dinero cobrado**, y es donde el retorno deja de ser una proyección.

## El flujo

```
viaje cerrado ──► svc-doc-checklist: ¿expediente completo?
                  │
                  ├─ no ─► D3-05 pide el faltante        (plantilla fija de svc-notify)
                  │        el viaje NO avanza
                  │
                  └─ sí ─► svc-invoicing arma el borrador
                           svc-cfdi-validate dictamina    (XSD + reglas SAT, sin LLM)
                           gate ──► Nay timbra            (ACT-DOC-S: HITL siempre)
                           svc-ar: aging, prioridad, flujo esperado
                           D2-04 explica la cartera y da seguimiento
                           svc-runlog registra cada paso, cada reintento y cada aprobación
```

## Por qué en este orden

1. **`svc-doc-checklist` primero.** Es la puerta que hace honesto todo lo de abajo: sin
   expediente completo no hay factura, y esa condición tiene que existir antes que la factura,
   no después. Además es el único de los cinco cuya dependencia es interna —el catálogo de
   requisitos de Fleeter— y por lo tanto el único que se puede empezar hoy mismo.
2. **`svc-invoicing`**, el hueco propiamente dicho.
3. **`svc-cfdi-validate`**, que se construye en paralelo pero **no se acepta sin CFDI reales**
   contra los cuales probar. Construirlo contra ejemplos de manual es la forma conocida de
   pasar por alto justo las reglas que rechaza el SAT.
4. **`svc-ar`**, que se apoya en la normalización bancaria que la Fase 0 ya dejó hecha.
5. **`svc-notify`** al final por tamaño, no por importancia: ninguno de los dos agentes puede
   pedir un documento faltante sin él.

## Lo que va a hacer segura la Fase 2

### El expediente incompleto no es una advertencia

`expediente_completo` es un booleano duro y es entrada obligatoria de `svc-invoicing`. Un viaje
sin POD firmado **no llega a tener borrador de factura**; no depende de que alguien lo note al
revisar. Es la misma forma del gate de margen de la Fase 1: la condición se aplica en el código
que produce el objeto, no en la revisión de quien lo recibe.

### El timbrado nunca lo hace un agente

`ACT-DOC-S` es `CTL-HITL` **siempre**, por regla dura del §11.4 — no por umbral, no por monto.
`D2-04` prepara; Nay timbra. Que el agente arme el 100% del borrador y ejecute el 0% del
timbrado es exactamente el reparto que hace que valga la pena encenderlo.

### El aviso al cliente no pasa por un modelo

`svc-notify` renderiza plantillas fijas con variables validadas. Esa propiedad es la que permite
que un aviso a cliente **no** sea HITL (§11.4): el texto ya lo aprobó una persona una vez, y el
sistema sólo rellena huecos que valida antes de enviar. En el momento en que un mensaje externo
lo redacte el modelo, vuelve a ser HITL — y eso es una decisión de diseño, no una restricción
que se pueda relajar por conveniencia.

### La prioridad de cobranza es una regla, no una opinión

`svc-ar` calcula a quién se le cobra primero. El §9.1 pone la prioridad de cobranza en la lista
de rankings con consecuencia: los produce el servicio con una regla versionada, y el agente los
narra. Un modelo decidiendo a qué cliente se le aprieta es un sesgo con factura.

## Condiciones de entrada — lo que tiene que pasar antes de construir

| Condición | Estado | Quién |
|---|---|---|
| Fase 1 encendida: `D4-03` y `D2-03` operando, no sólo declarados | **Pendiente** — ver [fase-1.md](fase-1.md) | Nay / Gabriel / `D5-01` |
| Bandeja única de HITL del ERP en producción | **Pendiente** — `E-001`, el primer hito del backlog | `D5-01` |
| Catálogo de requisitos documentales por tipo de servicio | **Pendiente** | Elias con Nay |
| Muestra de CFDI y Carta Porte reales de Fleeter | **Pendiente** | Nay |
| Umbral de cobranza calibrado (`authority-gate.yaml` lo tiene en `calibrado: false`) | **Pendiente** | Nay decide con Gabriel |
| Viajes cerrados reales cargados por `svc-ingest` | **Pendiente** | Nay |

La primera no es una formalidad de secuencia. La Fase 2 le entrega trabajo a dos agentes nuevos
sobre una infraestructura —presupuesto, trazabilidad, bandeja de HITL— que **todavía no ha
llevado un solo caso real de punta a punta**. Encender cuatro agentes sobre un gobierno sin
estrenar es duplicar la superficie de error antes de conocerla.

## Decisiones que hay que tomar, con dueño

Cada contrato las lleva en su propio `decisiones_pendientes`; aquí están juntas porque son lo
que de verdad bloquea el arranque:

| Decisión | Dónde pega | Quién |
|---|---|---|
| Qué documentos exige Fleeter por tipo de servicio | `svc-doc-checklist` — es su catálogo entero | Elias / Gabriel |
| Dónde viven los archivos de evidencia y qué se guarda (ruta, hash o archivo) | `svc-doc-checklist`, `CTL-PRIVACY` | `D5-01` / Vera |
| Qué PAC se usa y si el timbrado entra por API en esta fase | `svc-invoicing` | Nay / Gabriel |
| Catálogo de conceptos, series y folios vigentes | `svc-invoicing`, `svc-masterdata` | Nay |
| Cómo se cobran demoras y estadías hoy | `svc-invoicing` | Ana / Gabriel |
| Versión de CFDI y Carta Porte, y de dónde salen XSD y catálogos SAT | `svc-cfdi-validate` | Nay / contador |
| Cómo se concilia un pago sin referencia bancaria | `svc-ar` | Nay |
| Qué plantillas existen y quién las aprueba | `svc-notify` | Ana / Gabriel |

Emitir el borrador sin timbrar ya captura la mayor parte del ahorro. Si el PAC se atora, la fase
**no se detiene**: se construye hasta el borrador y el timbrado sigue siendo manual, que es como
está hoy.

## Lo que la Fase 2 no incluye

Escrito para que no se cuele por el camino:

* **Cancelación y reemisión de CFDI.** Es un proceso con reglas propias del SAT y no cabe dentro
  de un validador. Entra cuando exista, con su propio contrato.
* **Complemento de pago.** Depende de la conciliación bancaria fina; se decide al construir `svc-ar`.
* **Conciliación bancaria automática completa.** La Fase 0 normaliza el movimiento; casar el
  pago con su factura sin referencia es un problema aparte.
* **Cobranza judicial o extrajudicial.** Es de `D6-01`, fase 6.
* **Identidad en la oficina virtual para `D3-05` y `D2-04`.** Los contratos existen; el nombre,
  el escritorio y la memoria se les ponen cuando la fase arranque. Una silla con nombre para
  alguien que no va a sentarse en meses es ruido en el plano.

## Cómo se verifica que está preparada

```bash
python scripts/validate_registry.py --verbose   # 14 reglas en verde, con los pendientes listados
python -m pytest tests/validation                # el registro de la Fase 2, comprobado
```

Los servicios `planned` **declaran sus pruebas antes de existir**: esos nombres son el criterio
de aceptación de cada uno. La regla 7b los reporta como pendientes en vez de exigirlos —y falla
en el momento en que un servicio pase a `built` con una prueba declarada que nadie escribió.
