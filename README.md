# AI-company

Oficina Virtual de Agentes IA para una empresa de logística y transporte.

**Arquitectura vigente: [docs/arquitectura-v3.md](docs/arquitectura-v3.md)**

```
Capa organizacional   8 departamentos · 42 equipos          (cuesta cero tokens)
Capa ejecutable       1 orquestador + 32 agentes de dominio  = 33 agentes IA
Capa determinística   31 servicios Python                    (costo cero, testeable)
Capa de consultoría   9 consultores técnicos bajo demanda    (nunca encendidos, sin ACT-*)
Capa de control       Gate de Autoridad · HITL · ACT-* · RBAC · bitácora · privacidad
```

Principio central:

> La empresa se organiza como corporativo. Los procesos se ejecutan como software.
> Los agentes razonan, redactan y coordinan. Los servicios calculan, validan y accionan.
> Los humanos autorizan lo crítico.

Ningún cálculo numérico ocurre dentro del modelo.

Los consultores (`C-01`…`C-09`) son la excepción a la regla de "todo agente pertenece a un flujo":
**no pertenecen a ninguno.** Construyen el ERP cuando se les convoca y no tocan la operación.

**MVP: 5 agentes y 18 servicios**, alcanzado al cerrar la fase 3 (~16 semanas). Las fases 4–7 no se
encienden hasta que el MVP demuestre retorno medible. La proporción no es un accidente: la mayor
parte del valor temprano es código determinístico, no modelo.

## Qué aporta la v3 sobre la v2

| | |
|---|---|
| Capa organizacional | Reinstalada: 42 equipos con owner humano y digital. La v2 la había eliminado |
| Líderes de departamento | Rol de gobierno (políticas, KPIs, umbrales, escalamiento), sin llamada LLM |
| Trazabilidad de proceso | `svc-runlog`: `trace_id` por caso, cada paso, cada reintento, cada decisión del Gate |
| Progreso consultable | Estado del caso como máquina de estados, sin invocar LLM |
| Comunicación con personas | Contrato de entregable obligatorio + bandeja única de HITL con SLA |
| Antisesgo | Rúbrica versionada para todo ranking con consecuencia, no sólo para personas |
| Correcciones de conteo | Los equipos son 42 (no 31); los servicios eran 30 (no 29) y ahora son 31 |

El motor ejecutable —los 33 agentes, sus IDs y sus fusiones— es idéntico al de la v2 y ya fue
auditado ahí. La v3 añade el gobierno alrededor del motor.

## Documentos

- [docs/arquitectura-v3.md](docs/arquitectura-v3.md) — **vigente**.
- [docs/arquitectura-v2.md](docs/arquitectura-v2.md) — histórico. Contiene la auditoría de errores
  de la v1 y la justificación de cada consolidación de agente.
- [docs/arquitectura-v1.md](docs/arquitectura-v1.md) — histórico. Los 108 agentes originales
  (1 orquestador + 8 líderes + 99 núcleo). Ya verificado contra la columna "Absorbe A##" de la v3.
- [docs/owners-equipos.csv](docs/owners-equipos.csv) — los 42 equipos con owner y carga compartida.
- [docs/umbrales.md](docs/umbrales.md) — estado de calibración del Gate de Autoridad.
- [docs/fase-0.md](docs/fase-0.md) — **la Fase 0 construida**: cómo se corre, qué datos espera,
  la fórmula de costeo y el requisito de salida hacia la Fase 1.
- [docs/fase-1.md](docs/fase-1.md) — **la Fase 1 construida**: trazabilidad, validación,
  presupuesto, el gate de cotización y los dos primeros agentes de operación.
- [docs/fase-2.md](docs/fase-2.md) — **la Fase 2 construida**: expediente, comprobante,
  validación del SAT, cartera y avisos por plantilla.
- [docs/fase-3.md](docs/fase-3.md) — **la Fase 3 preparada**: contratos, orden de construcción,
  condiciones de entrada y las decisiones que faltan, con dueño.
- [docs/oficina-virtual.md](docs/oficina-virtual.md) — **los agentes del ERP y su oficina**: quién
  es quién, cómo se convoca, dónde vive su memoria y cómo se lee el plano.

## Estado

**Congelada como `v3.0.1`. Los cinco pendientes del §17 están cerrados.** Owners poblados desde
el organigrama de Fleeter con modelo de propiedad compartida, 6 de 10 umbrales calibrados con
cifras reales, bandeja única de HITL en Airtable, rúbricas reclasificadas a pre-Fase 7 y la v1
cargada — que al verificarse destapó dos agentes de la v1 perdidos sin justificación, ya
corregidos. Detalle en [§17](docs/arquitectura-v3.md#17-estado-de-cierre-de-la-v3).

**La Fase 0 está construida.** Cuatro servicios determinísticos, cero agentes, cero `ACT-*`:

| | |
|---|---|
| `svc-masterdata` | Catálogo único con integridad referencial y tabla de tarifas versionada |
| `svc-ingest` | Banco, tickets de diesel, GPS y CSV del ERP, con cuarentena por fila |
| `svc-costing` | Ocho conceptos de costo, costo por km, supuestos declarados |
| `svc-profitability` | Margen por viaje, ruta, cliente, unidad y operador, con distribución |

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m services.cli fase0 --datos data/ejemplo   # costo por km y margen real
.venv/Scripts/python -m pytest                                    # 239 pruebas
.venv/Scripts/python scripts/validate_registry.py --verbose  # §10.3
```

Detalle y requisito de salida hacia la Fase 1 en [docs/fase-0.md](docs/fase-0.md). La Fase 1 no
arranca hasta calibrar margen objetivo y mínimo por ruta con la distribución real que produce
`svc-profitability` ([umbrales.md](docs/umbrales.md)).

**La Fase 1 está construida.** Cinco servicios más y los dos primeros agentes de operación
declarados enteros —y apagados:

| | |
|---|---|
| `svc-runlog` | Registro append-only del camino y el progreso de cada caso, con SLA en horas hábiles |
| `svc-trace` | Cada cifra con su origen; bloquea el entregable que cita un número sin respaldo |
| `svc-validation` | Los seis campos del contrato de entregable y las reglas de dominio |
| `svc-budget` | Tope mensual por agente, alerta al 80%, corte duro al 100% |
| `svc-pricing` | Precio contra la tabla pre-aprobada, con el gate de margen mínimo |
| `D4-03` · `D2-03` | Pricing y Costos: declarados, con `ACT-*` sin otorgar y encendido pendiente |

```bash
python -m services.cli cotizar --ruta R-MTY-CDMX --unidad U-101 --cliente CL-01 --operador OP-01
```

Una cotización bajo el margen mínimo **no se genera**: no depende de que el modelo lo note.

`D4-03` Pricing y `D2-03` Costos existen enteros —contrato, prompt, memoria y escritorio— en un
estado nuevo, **`listo`**: ni `planned` (no existen) ni `built` (nadie puede convocarlos). El
runtime rechaza la convocatoria nombrando la condición que falta y quién la cierra, y la regla 13
del validador falla si un agente `listo` no declara esa lista. Detalle y condiciones de encendido
en [docs/fase-1.md](docs/fase-1.md).

**La Fase 2 está construida.** Cinco servicios más y los dos agentes que cierran el ciclo
operación → ingreso, otra vez declarados y sin encender:

| | |
|---|---|
| `svc-doc-checklist` | Si el expediente del viaje está completo. Sin él no hay factura |
| `svc-invoicing` | El comprobante armado entero; timbrarlo es `ACT-DOC-S`: HITL siempre |
| `svc-cfdi-validate` | Estructura, catálogo y aritmética del CFDI y la Carta Porte |
| `svc-ar` | Aging que no rejuvenece, prioridad con rúbrica y flujo esperado |
| `svc-notify` | Plantillas fijas con variables validadas, sin LLM en el camino |
| `D3-05` · `D2-04` | Evidencias y Cierre · Ciclo de Ingreso. `listo`, sin encender |

```bash
python -m services.cli facturar --viaje T-1001 --cliente CL-01 --flete 26500 \
    --documentos orden_de_servicio,carta_porte,pod --fecha 2026-06-01
python -m services.cli cartera --datos data/ejemplo --corte 2026-06-30
```

`facturar` **nunca sale con 0**: el comprobante queda esperando una firma humana. Un viaje sin
expediente completo no llega siquiera a tener borrador, y no quema un folio en el intento.

Cinco cosas que este código declara de sí mismo, porque un servicio que se presenta como más
completo de lo que es da permiso para no mirar: `svc-cfdi-validate` **no sustituye la validación
XSD del SAT**, los catálogos son un subconjunto fijado a mano, y el catálogo documental, la
política fiscal y la rúbrica de cobranza siguen **sin confirmar** — cada salida lo dice. Ninguna
de las cinco se cierra escribiendo código: se cierran confirmando un YAML.
Detalle en [docs/fase-2.md](docs/fase-2.md).

**La Fase 3 está preparada, no construida.** Cuatro servicios y el agente que cierran el corte
de MVP (§15: 5 agentes IA + 18 servicios), declarados en el registro y sin una línea de código
nueva:

| | |
|---|---|
| `svc-treasury` | Posición de caja, flujo proyectado y días de caja |
| `svc-ap` | Calendario de pagos, vencimientos y prioridad |
| `svc-kpi` | Indicadores homologados por departamento, con semáforo |
| `svc-alerts` | Motor de reglas: qué alerta se genera y qué entra al brief |
| `D1-03` | Síntesis Ejecutiva. Declarado, `planned` |

Un servicio `planned` **declara sus pruebas antes de existir**: esos nombres son su criterio de
aceptación, y el validador los reporta como pendientes hasta que el servicio pase a `built`.
Qué falta decidir y quién lo decide, en [docs/fase-3.md](docs/fase-3.md).

**La oficina virtual está abierta otra vez.** La pausa se levantó al cumplirse las dos
condiciones que ella misma escribía: los cinco servicios en verde y la bitácora del office
migrada a `svc-runlog`. El levantamiento queda en el mismo archivo que la pausa
([office/pausa.yaml](office/pausa.yaml)) — si el motivo y su cierre vivieran separados, en un mes
nadie sabría si se levantó por la condición o por prisa.

La bitácora de la oficina **ya no es un registro aparte**: es una vista de `svc-runlog`. Un
encargo y una cotización se responden desde el mismo archivo, con el mismo `trace_id` y la misma
máquina de estados. El histórico se importó conservando fecha y trace, sin reescribir el archivo
viejo:

```bash
python scripts/migrar_bitacora.py    # idempotente; el JSONL original no se toca
```

```bash
python -m office.cli estado      # quién está haciendo qué, y quién está listo sin encender
python -m office.cli build       # regenera office/oficina.html
start office/oficina.html        # el plano en píxeles (macOS/Linux: open)
```

Detalle en [docs/oficina-virtual.md](docs/oficina-virtual.md).
