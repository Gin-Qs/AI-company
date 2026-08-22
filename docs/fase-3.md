# Fase 3 — Visibilidad ejecutiva

**Preparada, no construida.** Cuatro servicios y un agente declarados en el registro; cero
líneas de código nuevas y cero agentes encendidos. Cierra el corte de MVP de la arquitectura
v3 (§15): **5 agentes IA + 18 servicios**.

Preparar una fase aquí significa una cosa concreta: **escribir qué va a hacer cada pieza, qué
pruebas la van a aceptar y qué decisiones faltan, antes de construirla.** Un contrato escrito
después del código es una descripción; escrito antes es un criterio.

| Pieza | Contrato | Qué resuelve |
|---|---|---|
| `svc-treasury` | [yaml](../registry/services/svc-treasury.yaml) | Posición de caja, flujo proyectado y días de caja |
| `svc-ap` | [yaml](../registry/services/svc-ap.yaml) | Calendario de pagos, vencimientos y prioridad |
| `svc-kpi` | [yaml](../registry/services/svc-kpi.yaml) | Indicadores homologados por departamento, con semáforo |
| `svc-alerts` | [yaml](../registry/services/svc-alerts.yaml) | Motor de reglas: qué alerta se genera y qué entra al brief |
| `D1-03` Síntesis Ejecutiva | [yaml](../registry/agents/D1-03-sintesis-ejecutiva.yaml) | Narra el brief diario; no calcula ni selecciona |

## Qué agujero tapa

Las fases 0 a 2 dejaron el costo, el precio y el cobro. Ninguna de las tres deja un lugar donde
Dirección vea la foto completa sin pedirle a alguien que arme un Excel. Esta fase es la primera
en no cerrar un ciclo de operación: cierra un ciclo de **lectura**, y es la que hace que el
retorno de las tres anteriores sea visible todos los días sin esperar a un corte de mes.

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

## Por qué en este orden

1. **`svc-treasury` primero.** Es el único de los cuatro que no depende de otro servicio nuevo
   de esta fase: consume la normalización bancaria que la Fase 0 ya dejó hecha y el flujo
   esperado que `svc-ar` ya produce desde la Fase 2.
2. **`svc-ap`** en paralelo. Es el espejo de `svc-ar` del lado de lo que se paga, y alimenta a
   `svc-treasury` con el calendario de pagos para el flujo proyectado.
3. **`svc-alerts`**, que depende de `svc-treasury` y `svc-ap` para tener algo que evaluar.
4. **`svc-kpi`** al final: empaqueta lo que las tres anteriores —y `svc-profitability` y
   `svc-ar` desde fases previas— ya calcularon. Sin ellas no tiene qué mostrar.
5. **`D1-03`** se enciende sobre el resultado de las cuatro. No hay ruta en la que narre antes
   de que exista lo que va a narrar.

## Lo que va a hacer segura la Fase 3

### El agente no elige qué ve Dirección

`svc-alerts` selecciona qué alerta entra al brief; `D1-03` narra la selección y **no puede
omitir ni añadir temas** (§9.2, límite duro). Si el modelo eligiera el contenido, el sesgo
entraría en lo primero que Dirección lee cada día, sin que nadie lo notara. La selección vive
en reglas versionadas sobre umbrales, no en el criterio de una corrida.

### Un KPI sin fuente declarada no se reporta

`svc-kpi` no calcula ninguna métrica: las toma de quien ya las calculó (`svc-profitability` el
margen, `svc-ar` el DSO, `svc-treasury` los días de caja) y las homologa con semáforo. Es la
regla R2 del §9 —**un número, una fuente**— aplicada a la capa de reporte: dos formas de llegar
al mismo indicador es la manera más rápida de que dos personas defiendan cifras distintas en la
misma junta.

### El mensaje de la alerta no lo redacta un modelo

Cada alerta que produce `svc-alerts` es una plantilla armada con datos —igual que `svc-notify`
en la Fase 2—, no texto generado. `D1-03` recibe el mensaje ya armado y lo integra en la
narrativa del brief; no lo inventa, y no puede citar una cifra que `svc-alerts` no haya
producido.

### El calendario de pagos no ejecuta el pago

`svc-ap` propone un calendario y una prioridad; no mueve un peso. Ejecutar el pago es
`ACT-PAY`, y `ACT-PAY` no existe hasta `D2-05` en la Fase 4, con doble factor y `CTL-HITL` por
regla dura de `authority-gate.yaml`. Adelantar la ejecución sería adelantar el riesgo sin
adelantar el control.

## Condiciones de entrada — lo que tiene que pasar antes de construir

| Condición | Estado | Quién |
|---|---|---|
| Fase 2 encendida: `D3-05` y `D2-04` operando, no sólo declarados | **Pendiente** — ver [fase-2.md](fase-2.md) | Nay / Gabriel / `D5-01` |
| Bandeja única de HITL del ERP en producción | **Pendiente** — `E-001`, el primer hito del backlog | `D5-01` |
| Saldo inicial de caja real para `svc-treasury` | **Pendiente** — hoy se declara como parámetro | Nay |
| Umbral de días de caja mínimo, para `svc-alerts` | **Pendiente** — propuesta de 90 días sin confirmar | Nay decide con Gabriel |
| Catálogo de KPIs con metas aprobadas por departamento | **Pendiente** — hoy son propuestas | Gabriel |
| Cuentas por pagar reales cargadas para `svc-ap` | **Pendiente** | Nay |

La primera no es una formalidad de secuencia, igual que en la Fase 2: encender un quinto agente
sobre una infraestructura de gobierno que todavía no llevó un caso real de punta a punta
duplica la superficie de error antes de conocerla.

## Decisiones que hay que tomar, con dueño

Cada contrato las lleva en su propio `decisiones_pendientes`; aquí están juntas porque son lo
que de verdad bloquea el arranque:

| Decisión | Dónde pega | Quién |
|---|---|---|
| Saldo inicial de caja y si hay integración bancaria para leerlo | `svc-treasury` | Nay |
| Umbral de días de caja mínimo | `svc-alerts` (`registry/policies/alertas.yaml`) | Nay / Gabriel |
| Umbral de brecha de margen que dispara alerta | `svc-alerts` | Nay |
| Catálogo de proveedores: no existe en `svc-masterdata` | `svc-ap` | `D5-01` / Nay |
| Política de priorización de pago | `svc-ap` (`registry/policies/rubrica-pagos.yaml`) | Nay / Gabriel |
| Metas por KPI y departamento | `svc-kpi` (`registry/policies/kpis.yaml`) | Gabriel |

Ninguna de las seis se cierra escribiendo código: se cierran confirmando un YAML o cargando un
dato real, igual que en la Fase 2.

## Lo que la Fase 3 no incluye

Escrito para que no se cuele por el camino:

* **Ejecución de pagos.** `svc-ap` propone; ejecutar es `ACT-PAY` de `D2-05`, fase 4.
* **Estados financieros completos (EEFF, EBITDA, ROIC).** Es `svc-financials`, fase 4: depende
  de una contabilidad que esta fase no construye.
* **Escenarios y sensibilidad.** Es `svc-scenarios`, fase 4.
* **Estrategia o aprobación de inversión.** Es `D1-01`, fase 7. `D1-03` narra; no recomienda
  una decisión de dirección.
* **Identidad en la oficina virtual para `D1-03`.** El contrato existe; el nombre, el
  escritorio y la memoria se le ponen cuando la fase arranque.

## Cómo se verifica que está preparada

```bash
python scripts/validate_registry.py --verbose   # 14 reglas en verde, con los pendientes listados
python -m pytest tests/validation                # el registro de la Fase 3, comprobado
```

Los cuatro servicios `planned` **declaran sus pruebas antes de existir**: esos nombres son el
criterio de aceptación de cada uno. La regla 7b los reporta como pendientes en vez de
exigirlos —y falla en el momento en que un servicio pase a `built` con una prueba declarada
que nadie escribió.
