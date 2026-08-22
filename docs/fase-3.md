# Fase 3 — Visibilidad ejecutiva

**Construida. Cuatro servicios determinísticos y un agente `listo`, sin encender.**

Las fases 0 a 2 dejaron el costo, el precio y el cobro. Ésta es la primera que no cierra un
ciclo de operación: cierra un ciclo de **lectura**. Cierra también el corte de MVP de la
arquitectura v3 (§15): **5 agentes IA + 18 servicios**. Aquí se para y se evalúa — nada de las
fases 4–7 se enciende sin que el MVP demuestre retorno medible.

| Pieza | Módulo | Contrato | Qué resuelve |
|---|---|---|---|
| `svc-treasury` | [services/treasury/](../services/treasury/) | [yaml](../registry/services/svc-treasury.yaml) | Posición de caja, flujo proyectado y días de caja |
| `svc-ap` | [services/ap/](../services/ap/) | [yaml](../registry/services/svc-ap.yaml) | Calendario de pagos, vencimientos y prioridad |
| `svc-kpi` | [services/kpi/](../services/kpi/) | [yaml](../registry/services/svc-kpi.yaml) | Indicadores homologados por departamento, con semáforo |
| `svc-alerts` | [services/alerts/](../services/alerts/) | [yaml](../registry/services/svc-alerts.yaml) | Motor de reglas: qué alerta se genera y qué entra al brief |
| `D1-03` Síntesis Ejecutiva | — | [yaml](../registry/agents/D1-03-sintesis-ejecutiva.yaml) | Narra el brief diario; no calcula ni selecciona |

```bash
python -m services.cli brief --datos data/ejemplo --corte 2026-06-30 --saldo-inicial 10000
```

`brief` sale con código `0`: es informativo, no hay un gate que bloquee la salida. Lo que sí
está controlado es qué alerta llega a la sección final — exactamente la misma lista que `D1-03`
podría narrar, y ni una más.

## Qué agujero tapa

Las fases 0 a 2 dejaron el costo, el precio y el cobro, pero ninguna deja un lugar donde
Dirección vea la foto completa sin pedirle a alguien que arme un Excel. Esta fase produce esa
foto todos los días, con las mismas cifras que ya produjo el resto del sistema.

## El flujo

```
svc-treasury    posición de caja, flujo proyectado, días de caja  ◄── movimientos (svc-ingest)
     │                                                            ◄── cobros esperados (svc-ar)
     │                                                            ◄── pagos esperados (svc-ap)
     ▼
svc-alerts      evalúa reglas sobre umbrales: liquidez, margen, vencimientos
     │          selecciona qué entra al brief (§9.2) — el agente no elige
     ▼
svc-kpi         empaqueta indicadores ya calculados, con semáforo contra meta
     │
     ▼
D1-03           narra el brief con lo que svc-alerts seleccionó y lo que svc-kpi empaquetó
                no genera un número, no añade ni quita un tema
```

Probado de punta a punta en
[tests/integration/test_flujo_fase3.py](../tests/integration/test_flujo_fase3.py), incluido el
camino en que una alerta se calcula y se guarda pero no llega al brief por su severidad.

## Lo que hace segura la Fase 3

### El agente no elige qué ve Dirección

`svc-alerts` selecciona qué alerta entra al brief; `D1-03` narra la selección y **no puede
omitir ni añadir temas** (§9.2, límite duro). Cada `Alerta` calcula su propio
`entra_al_brief` al construirse, comparando severidad contra `severidad_minima_brief` de
`registry/policies/alertas.yaml` — no es un campo que se ajuste después ni un criterio de quien
lea la lista.

[tests/unit/test_cli_fase3.py](../tests/unit/test_cli_fase3.py) prueba exactamente esta forma:
el comando `brief` calcula una alerta de severidad media y la muestra en el bloque de
`ALERTAS`, pero esa misma alerta no aparece en el bloque final `BRIEF (lo que D1-03 narraría)`.

### Un KPI sin fuente declarada no se reporta

`svc-kpi` no calcula ninguna métrica: las toma de quien ya las calculó — `svc-profitability` el
margen, `svc-ar` el DSO, `svc-treasury` los días de caja — y las homologa con semáforo contra
la meta de `registry/policies/kpis.yaml`. Es la regla R2 del §9 —**un número, una fuente**—
aplicada a la capa de reporte. Pedir un KPI que no está en el catálogo levanta `KPIDesconocido`
en vez de reportar un cero silencioso.

### El mensaje de la alerta no lo redacta un modelo

Cada alerta que produce `svc-alerts` es una f-string armada con los datos de la propia alerta
—igual que `svc-notify` en la Fase 2—, no texto generado. Los mismos datos producen siempre el
mismo mensaje: es lo que prueba
`test_el_mensaje_de_la_alerta_no_pasa_por_llm`.

### El calendario de pagos no ejecuta el pago

`svc-ap` propone un calendario y una prioridad; no mueve un peso. Ejecutar el pago es
`ACT-PAY`, y `ACT-PAY` no existe hasta `D2-05` en la Fase 4, con doble factor y `CTL-HITL` por
regla dura de `authority-gate.yaml`. Adelantar la ejecución sería adelantar el riesgo sin
adelantar el control.

### El saldo de caja no se inventa

`svc-treasury` corre el saldo día a día sobre movimientos bancarios reales de `svc-ingest`; el
saldo inicial se recibe declarado porque no hay integración que lo lea del banco. Sin gasto
histórico, `dias_de_caja` es `None` — indeterminado, no infinito. Una caja que nunca ha gastado
no es una caja que "aguanta para siempre".

## Los límites que este código declara de sí mismo

| Límite | Dónde se ve |
|---|---|
| El umbral de días de caja mínimo es una **propuesta** de 90 días | `calibrado: false` en `alertas.yaml` y en cada `Seleccion.reglas_calibradas` |
| El umbral de brecha de margen que dispara alerta sigue sin confirmar | mismo archivo, mismo campo |
| `svc-ap` no tiene catálogo de proveedores en `svc-masterdata` | `dias_credito` se recibe por cuenta, no por consulta — declarado en `decisiones_pendientes` |
| Las metas del tablero de KPIs son **propuestas**, no aprobadas | `aprobado: false` en `kpis.yaml` |
| `data/ejemplo` no tiene cuentas por pagar reales | el comando `brief` corre con un calendario de AP vacío, y se dice en el código, no se oculta |

Ninguno de los cinco se cierra escribiendo código: se cierran confirmando un YAML o cargando un
dato real, igual que en la Fase 2.

## El agente: completo y apagado

Igual que en las fases 1 y 2, `D1-03` (Isabel) está en estado **`listo`**: contrato completo,
prompt escrito, memoria puesta y encendido pendiente. A diferencia de los otros cuatro, no
declara ningún `ACT-*` — el brief es lectura interna, no comunicación externa — así que su
`model_tier` es `Bajo`: clasificación y síntesis de alta frecuencia, no juicio de negocio.

| Condición | `D1-03` |
|---|---|
| `svc-kpi` y `svc-alerts` construidos y en verde | **Hecho** |
| Umbral de días de caja mínimo calibrado en `authority-gate.yaml`/`alertas.yaml` | Pendiente — Nay decide con Gabriel |
| Bandeja única de HITL del ERP en producción | Pendiente — `D5-01` |

La bandeja de HITL vuelve a aparecer aunque `D1-03` no tenga `ACT-*`: es el requisito de
entrada que comparten las cuatro primeras fases, no una condición atada sólo a quien ejecuta.

## ⬛ Corte de MVP

> **Agentes:** `D4-03`, `D2-03`, `D3-05`, `D2-04`, `D1-03` — los cinco.
> **Servicios:** los 18 de las fases 0 a 3.
>
> Aquí se para y se evalúa. Nada de las fases 4–7 se enciende sin que el MVP demuestre retorno
> medible: margen protegido en cotizaciones, días de cobro reducidos, brief diario confiable.
> Si el MVP no lo demuestra, el problema no se arregla añadiendo agentes.

## Decisiones que siguen abiertas, con dueño

| Decisión | Dónde pega | Quién |
|---|---|---|
| Saldo inicial de caja y si hay integración bancaria para leerlo | `svc-treasury` | Nay |
| Umbral de días de caja mínimo | `svc-alerts` (`registry/policies/alertas.yaml`) | Nay / Gabriel |
| Umbral de brecha de margen que dispara alerta | `svc-alerts` | Nay |
| Catálogo de proveedores: no existe en `svc-masterdata` | `svc-ap` | `D5-01` / Nay |
| Política de priorización de pago, proveedores críticos | `svc-ap` (`registry/policies/rubrica-pagos.yaml`) | Nay / Gabriel |
| Metas por KPI y departamento | `svc-kpi` (`registry/policies/kpis.yaml`) | Gabriel |

## Deudas declaradas

* **`svc-ap` no tiene cuentas por pagar reales cargadas.** El servicio está probado con datos
  sintéticos y el comando `brief` corre con un calendario vacío sobre `data/ejemplo` — una
  salida válida, no un error, pero no representa lo que la operación paga de verdad.
* **No entra en esta fase:** estados financieros completos (`svc-financials`, fase 4),
  escenarios y sensibilidad (`svc-scenarios`, fase 4), y cualquier forma de aprobar o ejecutar
  un pago (`ACT-PAY`, `D2-05`, fase 4).

## Cómo se verifica

```bash
python -m pytest                                # 278 pruebas
python scripts/validate_registry.py --verbose   # 14 reglas en verde
python -m services.cli brief --datos data/ejemplo --corte 2026-06-30 --saldo-inicial 10000
```
