# Fase 2 — Cerrar el ciclo operación → ingreso

**Construida. Cinco servicios determinísticos y dos agentes `listo`, sin encender.**

La Fase 0 dejó el costo y la Fase 1 dejó el precio. Ésta es la que convierte el precio en dinero
cobrado, y es donde el retorno deja de ser una proyección.

| Pieza | Módulo | Contrato | Qué resuelve |
|---|---|---|---|
| `svc-doc-checklist` | [services/doc_checklist/](../services/doc_checklist/) | [yaml](../registry/services/svc-doc-checklist.yaml) | Si el expediente del viaje está completo |
| `svc-invoicing` | [services/invoicing/](../services/invoicing/) | [yaml](../registry/services/svc-invoicing.yaml) | El comprobante y su timbrado |
| `svc-cfdi-validate` | [services/cfdi_validate/](../services/cfdi_validate/) | [yaml](../registry/services/svc-cfdi-validate.yaml) | Si el CFDI y la Carta Porte cumplen |
| `svc-ar` | [services/ar/](../services/ar/) | [yaml](../registry/services/svc-ar.yaml) | Cartera, prioridad de cobranza y flujo esperado |
| `svc-notify` | [services/notify/](../services/notify/) | [yaml](../registry/services/svc-notify.yaml) | Avisos por plantilla fija, sin LLM |
| `D3-05` Evidencias y Cierre | — | [yaml](../registry/agents/D3-05-evidencias-y-cierre-de-viaje.yaml) | Persigue el documento que falta |
| `D2-04` Ciclo de Ingreso | — | [yaml](../registry/agents/D2-04-ciclo-de-ingreso.yaml) | Prepara la factura y sigue la cobranza |

```bash
python -m services.cli facturar --viaje T-1001 --cliente CL-01 --flete 26500 \
    --documentos orden_de_servicio,carta_porte,pod --fecha 2026-06-01
python -m services.cli cartera --datos data/ejemplo --corte 2026-06-30
```

`facturar` sale con código `1` **siempre**: el comprobante queda esperando una firma humana, y
con `3` cuando la puerta documental no lo deja pasar. No hay salida `0`, porque no hay camino en
el que este sistema emita una factura solo.

## Qué agujero tapa

La v1 tenía dieciséis agentes de operación y ninguno que cerrara el ciclo: la empresa movía
carga, cerraba viajes y **facturaba a mano**. El hueco no era de inteligencia, era de proceso —
por eso `D2-04` aparece en la arquitectura marcado como *hueco de facturación* y no como
absorción de un agente de la v1.

## El flujo

```
viaje cerrado ──► svc-doc-checklist: ¿expediente completo?
                  │
                  ├─ no ─► D3-05 pide el faltante        (plantilla fija de svc-notify)
                  │        el viaje NO avanza, y no se quema un folio
                  │
                  └─ sí ─► svc-invoicing arma el borrador
                           svc-cfdi-validate dictamina    (estructura, catálogo y aritmética)
                           gate ──► Nay timbra            (ACT-DOC-S: HITL siempre)
                           svc-ar: aging, prioridad, flujo esperado
                           svc-runlog registra cada paso, cada reintento y cada aprobación
```

Está probado de punta a punta en
[tests/integration/test_flujo_fase2.py](../tests/integration/test_flujo_fase2.py), incluido el
camino en que el expediente está incompleto y el caso queda bloqueado esperando un papel.

## Lo que hace segura la Fase 2

### El expediente incompleto no es una advertencia

`expediente_completo` es un booleano duro y es **entrada obligatoria** de `svc-invoicing`. Un
viaje sin POD no llega a tener borrador de factura: `armar_borrador()` cruza la puerta antes de
calcular un solo importe. Es la misma forma del gate de margen de la Fase 1 — la condición se
aplica donde se produce el objeto, no en la revisión de quien lo recibe.

Y el checklist distingue tres cosas que se resuelven distinto:

| | Qué significa | Qué hay que hacer |
|---|---|---|
| `falta` | el documento no está | buscarlo |
| `vencido` | está y su vigencia ya pasó | renovarlo |
| `no_corresponde` | es de otro viaje | quitarlo — es la forma más común de que un expediente se vea completo sin estarlo |

### El timbrado nunca lo hace un agente

`ACT-DOC-S` es `CTL-HITL` **siempre**, por regla dura del §11.4 — no por umbral, no por monto.
`timbrar()` levanta `TimbradoRequiereHumano` sin una autorización explícita, y **no existe un
parámetro que desactive esa condición**: el día que existiera, la regla dura pasaría a depender
de que nadie lo use.

Tampoco finge lo que no hace. Sin PAC contratado, un comprobante autorizado queda en
`pendiente_pac`. Devolver un UUID inventado sería mucho peor que devolver "pendiente".

### El concepto sin papel no se cobra — y el que tiene papel no se pierde

Una estadía que nadie firmó no se factura. Y una estadía firmada no se cae del comprobante: ese
segundo caso es el más común y el más caro, porque es trabajo hecho que se pierde por no
adjuntar un papel. El enlace entre concepto y documento vive en
[`requisitos-documentales.yaml`](../registry/policies/requisitos-documentales.yaml), no en el
criterio de quien factura ese día.

### El aviso al cliente no pasa por un modelo

`svc-notify` renderiza plantillas aprobadas con variables validadas. Esa propiedad es la que
permite que un aviso a cliente **no** sea HITL (§11.4). No hay parámetro para texto libre, una
variable con el tipo equivocado detiene el mensaje, y el destinatario existe en `svc-masterdata`
o no hay envío. `Mensaje.paso_por_llm` es una constante con nombre: el día que pudiera ser
`True`, el gate cambia.

Sin canal externo contratado, el mensaje queda `registrado_para_envio_humano`. Decir "enviado"
sin haber enviado es la clase de mentira que nadie detecta hasta que el cliente reclama.

### La prioridad de cobranza es una regla, no una opinión

El §9.1 pone la prioridad de cobranza entre los rankings con consecuencia: la calcula `svc-ar`
con la [rúbrica versionada](../registry/policies/rubrica-cobranza.yaml) y la versión viaja en
cada fila del resultado. Un modelo decidiendo a qué cliente se le aprieta es un sesgo con
factura.

Dos decisiones del aging que valen más que su tamaño:

* **Un pago parcial reduce el saldo; no rejuvenece la factura.** Una factura de hace cien días
  con abono de ayer sigue siendo de hace cien días.
* **Un depósito sin referencia no se reparte.** Repartirlo entre las facturas más viejas es lo
  que hace una hoja de cálculo, y es la razón por la que la cartera nunca cuadra: el saldo se ve
  bien y el cliente reclama una factura que ya pagó. Aquí queda a la vista, en su propio renglón.

## Los límites que este código declara de sí mismo

Un servicio que se presenta como más completo de lo que es sería peor que no tenerlo: daría
permiso para no mirar. Los tres límites están en el contrato, en la salida y en las pruebas.

| Límite | Dónde se ve |
|---|---|
| `svc-cfdi-validate` **no sustituye la validación XSD del SAT** | `valida_xsd: false` en el contrato y en cada dictamen |
| Los catálogos del SAT son un **subconjunto fijado a mano** | `catalogo_completo: false` y una advertencia en cada dictamen |
| El catálogo documental **no está confirmado** por la operación | `catalogo_confirmado: false` en cada expediente |
| La política fiscal **no está confirmada** por Nay | `politica_confirmada: false` en cada borrador |
| La rúbrica de cobranza **no está calibrada** | `rubrica_calibrada: false` en cada cartera |

Ninguno de esos cinco se cierra escribiendo código: se cierran confirmando un YAML.

## Los dos agentes: completos y apagados

Igual que en la Fase 1, `D3-05` (Sofía) y `D2-04` (Ximena) están en estado **`listo`**: contrato,
prompt, memoria y escritorio, y el runtime rechaza toda convocatoria nombrando lo que falta.

| Condición | `D3-05` | `D2-04` |
|---|---|---|
| Servicios de la fase construidos y en verde | **Hecho** | **Hecho** |
| Catálogo de requisitos documentales confirmado | Pendiente — Elias | — |
| Muestra de CFDI y Carta Porte reales de Fleeter | — | Pendiente — Nay |
| Umbral de cobranza calibrado en `authority-gate.yaml` | — | Pendiente — Nay decide con Gabriel |
| Bandeja única de HITL del ERP en producción | Pendiente — `D5-01` | Pendiente — `D5-01` |

La bandeja de HITL vuelve a aparecer, y no por casualidad: es el requisito de entrada que
comparten las tres primeras fases. `D2-04` sin bandeja es un agente que prepara comprobantes que
nadie puede firmar.

## Decisiones que siguen abiertas, con dueño

| Decisión | Dónde pega | Quién |
|---|---|---|
| Qué documentos exige Fleeter por tipo de servicio | `requisitos-documentales.yaml` — hoy es una propuesta | Elias / Gabriel |
| Dónde viven los archivos de evidencia (ruta, hash o archivo) | `svc-doc-checklist`, `CTL-PRIVACY` | `D5-01` / Vera |
| Qué PAC se usa y si el timbrado entra por API | `facturacion.yaml` — hoy `pac: null` | Nay / Gabriel |
| Series, folios y claves de producto vigentes | `facturacion.yaml`, `svc-masterdata` | Nay |
| Cómo se cobran demoras y estadías | `svc-invoicing` | Ana / Gabriel |
| Versión de CFDI y Carta Porte, y de dónde salen los XSD | `catalogos-sat.yaml` | Nay / contador |
| Cómo se concilia un pago sin referencia bancaria | `svc-ar` | Nay |
| Qué plantillas existen y quién las aprueba | `plantillas-notify.yaml` — hoy `aprobadas: false` | Ana / Gabriel |

## Deudas declaradas

* **La retención del 4% se deduce del RFC.** 12 posiciones = persona moral = retiene. Es una
  deducción del sistema, no un dato capturado, y viaja como supuesto en cada borrador. Un
  cliente mal capturado produce una retención mal aplicada, y esa diferencia aparece meses
  después en la conciliación.
* **La factura de un viaje se deduce de su ingreso** cuando la cartera se arma desde la
  operación (`python -m services.cli cartera`). Es una aproximación declarada, no un atajo
  escondido: mientras el ERP no emita el comprobante, es lo que hay.
* **No entra en esta fase:** cancelación y reemisión de CFDI —proceso con reglas propias del
  SAT—, complemento de pago, conciliación bancaria fina y cobranza legal (que es de `D6-01`,
  fase 6).

## Cómo se verifica

```bash
python -m pytest                                # 239 pruebas
python scripts/validate_registry.py --verbose   # 14 reglas en verde
python -m services.cli cartera --datos data/ejemplo --corte 2026-06-30
```
