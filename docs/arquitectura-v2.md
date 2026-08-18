# Oficina Virtual de Agentes IA — Arquitectura v2

> Versión corregida y optimizada de la propuesta original (108 agentes).
> **Resultado: 33 agentes IA + 29 servicios determinísticos**, con un MVP de 5 agentes y 8 servicios.

---

## 0. Resumen de la corrección

| | v1 (original) | v2 (esta propuesta) |
|---|---|---|
| Agentes IA | 108 | **33** |
| Servicios determinísticos (Python) | 0 | **29** |
| Líderes de departamento como agentes LLM | 8 | 0 (ruteo por configuración) |
| Agentes QA independientes | 9 | 0 (servicio transversal de validación) |
| Llamadas LLM por entregable típico | 4–6 | **1–2** |
| Cálculos numéricos hechos por el LLM | todos | **ninguno** |
| Agentes en el MVP | — | **5** |

El cambio de fondo es uno solo:

> **El LLM decide *qué* hacer y *redacta*. Python calcula, valida y ejecuta.**
> Ninguna habilidad `PR-CALC`, `PR-COMP`, `PR-ANOM`, `PR-SIM`, `PR-VAL` ni `PR-SCORE` se
> ejecuta dentro del modelo. Todas son funciones Python que el agente invoca como herramienta.

Consecuencias directas: el costo por km de una ruta sale **idéntico siempre**, es auditable línea
por línea, se prueba con `pytest`, y cuesta cero tokens.

---

## 1. Errores de v1 y cómo se corrigen

### 1.1 Errores duros de consistencia

| # | Error en v1 | Corrección en v2 |
|---|---|---|
| 1 | `PR-SCORE` se asigna a 7 agentes pero **no existe** en el catálogo §5.2 | Se define formalmente, y se reclasifica: el scoring lo produce un servicio con rúbrica explícita, no el LLM |
| 2 | `CTL-TRACE` (A4) **no existe**; es `PR-TRACE` | Corregido |
| 3 | `CTL-QA` (A46, A50) **no existe**; es `PR-QA` | Corregido |
| 4 | `CTL-POLICY` está definido pero **ningún agente lo usa** | Asignado a los agentes de Compliance y al gate de aprobación |
| 5 | §17 invoca un "agente líder operativo del equipo" que **no existe** en la arquitectura | Eliminado. El nivel "equipo" desaparece como capa ejecutable |
| 6 | El diagrama de §2 dibuja líderes, equipos y agentes como hermanos, contradiciendo §19 | Jerarquía explícita y única (§3 de este documento) |
| 7 | Dirección y Gobierno era el único departamento sin QA, y nadie auditaba al Orquestador | QA es transversal y cubre al Orquestador |

> Los conteos de v1 sí cuadraban: 99 núcleo, 31 equipos, 108 totales. Verificado equipo por equipo.

### 1.2 Errores de diseño

**E1 — Faltaba la capa de acción.** En v1 todas las habilidades eran de lectura (`IN-*`),
procesamiento (`PR-*`) o producción de artefactos (`OUT-*`). Ningún agente podía escribir en el
ERP. La oficina virtual generaba documentos que un humano tenía que recapturar a mano — es decir,
reintroducía la carga que se quería eliminar.
→ **Se añade la categoría `ACT-*`** (§4.5), con control obligatorio.

**E2 — Redundancia entre agentes.** Pares que hacían lo mismo:
`A65 ≈ A99`, `A64 ≈ A97/A98`, `A18 ≈ A74`, `A56 ≈ A67`, `A59 ≈ A68`,
`A19 ≈ A73 ≈ A91`, `A25 ≈ A35 ≈ A41`, `A9 ≈ A13`, `A10 ≈ A38`, `A61 ≈ A62`.
El caso más grave es `A10 vs A38`: el costeo se calculaba dos veces, en Finanzas y en Comercial,
con riesgo real de dar **dos números distintos para la misma ruta**.
→ Fusionados. El costeo vive en **un solo servicio** consumido por ambos departamentos.

**E3 — Nueve agentes QA.** A9, A13, A32, A40, A57, A87, A92, A97, A98.
Nueve agentes QA multiplican el costo de tokens sin multiplicar la confiabilidad: un LLM revisando
a otro LLM no da garantía.
→ **QA se convierte en `svc-validation`**: reglas determinísticas por dominio + muestreo humano.

**E4 — La regla §16.3 y el flujo §17 eran inviables en costo.**
"Agente → QA → Líder → Humano → Sistema" aplicado a *todo* implica mínimo 4 llamadas LLM por
entregable. Y el "flujo paralelo" de §18 (nuevo cliente grande → Comercial + Finanzas + Operaciones
+ Legal + Riesgos) activaba ~20 agentes para un solo lead.
→ **Ruteo por criticidad** (§7): sólo los entregables de criticidad alta pasan por el circuito
completo.

**E5 — Los límites no eran implementables.** §16.2 decía "pagos importantes", "riesgo alto".
Sin umbrales numéricos no se puede codificar `CTL-LIMIT` ni `CTL-HITL`. Además `CTL-ESC` y
`CTL-HITL` nunca se diferenciaban.
→ **Tabla de umbrales parametrizada** (§6.2) y definición separada de ambos controles.

**E6 — A98 era circular.** Detectar alucinaciones con un agente IA no da garantía.
→ `svc-trace`: verificación determinística de cada cifra contra su consulta origen. Si un número
del reporte no reconcilia con el query al ERP, el entregable se bloquea. Sin LLM de por medio.

**E7 — Tecnología estaba inflada 7×.** 22 agentes para frontend, backend, base de datos, QA
técnico, DevOps, monitoreo y documentación. Eso no es una oficina virtual: **es un desarrollador
usando Claude Code, GitHub Actions, Sentry y Metabase.**
→ Tecnología baja a 3 agentes de oficina. La ingeniería se documenta como capa de herramientas,
no como plantilla de agentes.

### 1.3 Huecos operativos que faltaban

| Hueco | Impacto | Solución en v2 |
|---|---|---|
| **Facturación / timbrado** | A31 armaba el "paquete de facturación" y A15 cobraba, pero **nadie emitía la factura**. Cadena operación → ingreso rota | `svc-invoicing` + agente `D2-04 Ciclo de Ingreso` |
| **Compras / procurement** | Diesel, llantas, refacciones y talleres son el mayor bloque de costo después de nómina. Sólo existían en CXP (pagar), no en negociar ni comparar | Absorbido por `D2-05 Ciclo de Egreso` con `svc-ap` |
| **Ingesta y calidad de datos de entrada** | Nadie normalizaba estados de cuenta, tickets de diesel ni feed GPS. A98 sólo cubría la salida de los agentes | `svc-ingest` |
| **Datos maestros** | Sin catálogo único de clientes, unidades, operadores, rutas y tarifas, los cálculos divergen | `svc-masterdata` — **prerrequisito de todo lo demás** |
| **Demoras / estadías** | Ingreso recurrente en transporte, ausente por completo | Incluido en `svc-invoicing` como concepto facturable |
| **Cobertura 24/7** | La Torre de Control implicaba operación continua sin modelo de turnos | `svc-telemetry` corre siempre (código); el agente sólo se activa ante excepción |

### 1.4 Riesgos de control y legales

**R1 — Comunicación externa sin control humano.** A15 (cobranza), A26 (avisos a cliente),
A37 (CRM) y A41 (atención) podían generar y enviar correos a clientes. §16.2 restringía pagos y
contratos, pero **no restringía comunicación saliente**. Un correo de cobranza con datos
equivocados a tu cliente es daño reputacional directo.
→ En v2 todo `ACT-EMAIL-S` externo requiere `CTL-HITL`, **salvo plantillas fijas con variables
validadas** (ej. "su unidad salió a las HH:MM"), que no pasan por LLM.

**R2 — Cero mención de datos personales.** Los agentes leen CVs, expedientes laborales, nómina y
GPS de operadores. En México eso cae bajo LFPDPPP.
→ `svc-privacy`: clasificación de PII, redacción antes de enviar al modelo, política de retención,
y prohibición de enviar expedientes completos al LLM.

**R3 — Scoring de personas.** A82 rankeaba candidatos, A22/A86 puntuaban operadores. Scoring con
LLM sobre personas es exposición por discriminación laboral.
→ El scoring de personas es **determinístico, con rúbrica versionada y atributos protegidos
excluidos por lista**. El LLM sólo extrae datos del CV; no puntúa. La decisión es humana y queda
registrada.

**R4 — Sin gobierno de costo.** Ningún presupuesto de tokens ni escalonamiento de modelo.
→ `svc-budget` + escalonamiento por niveles (§6.3).

---

## 2. Principios de la v2

1. **Determinismo primero.** Si se puede calcular, se calcula. El LLM es el último recurso, no el primero.
2. **Una sola fuente de verdad por número.** Un solo `svc-costing`. Un solo `svc-pricing`.
3. **El agente nunca afirma una cifra que no venga de una herramienta.** `svc-trace` lo verifica.
4. **La acción con efecto externo requiere autorización explícita y registrada.**
5. **Un agente por proceso de negocio, no por tarea.** Las tareas son herramientas.
6. **Todo agente se enciende sólo cuando produce retorno medible.** Fases, no big bang.

---

## 3. Arquitectura

```
                    Dirección Humana
                          │
                    ┌─────┴─────┐
                    │  Gate de  │   ← umbrales numéricos, HITL, bitácora
                    │ Autoridad │
                    └─────┬─────┘
                          │
                 Agente Orquestador (1)
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   32 Agentes IA    29 Servicios      Capa de Datos
   (8 dominios)     Determinísticos   (masterdata + ingest)
        │                 │                 │
        └────────► herramientas ◄───────────┘
```

**Se elimina la capa de "líder de departamento" como agente LLM.** En v1 eran 8 llamadas al modelo
por solicitud, sólo para enrutar. En v2 el ruteo es una tabla de configuración en el Orquestador.
La capa se reinstala sólo si un dominio supera ~8 agentes; hoy ninguno lo hace.

**Se elimina la capa de "equipo"** como unidad ejecutable. Sobrevive únicamente como etiqueta
organizativa en el registro.

---

## 4. Catálogo de habilidades corregido

### 4.1 Entrada (`IN-*`) — sin cambios respecto a v1
`IN-TXT` · `IN-PDF` · `IN-XLSX` · `IN-CSV` · `IN-IMG` · `IN-EMAIL` · `IN-ERP` · `IN-DB` ·
`IN-DASH` · `IN-DOCS` · `IN-GPS` · `IN-API`

### 4.2 Procesamiento por LLM (`PR-*`) — **reducido**
Sólo permanecen las que requieren juicio lingüístico:

| Código | Habilidad |
|---|---|
| `PR-CLASS` | Clasificación de texto ambiguo |
| `PR-EXT` | Extracción de documentos no estructurados |
| `PR-SUM` | Resumen |
| `PR-ROOT` | Análisis causa-raíz |
| `PR-RISK` | Evaluación cualitativa de riesgo |
| `PR-PRIOR` | Priorización con contexto de negocio |

**Retiradas del LLM y convertidas en servicios:**
`PR-CALC`, `PR-COMP`, `PR-VAL`, `PR-SIM`, `PR-ANOM`, `PR-TRACE`, `PR-QA`, `PR-SCORE`.
Siguen existiendo como capacidad — pero como llamada a `SVC-*`.

### 4.3 Servicios determinísticos (`SVC-*`) — **nueva categoría**
Declaran de qué servicio Python depende un agente. Ver §5.

### 4.4 Salida (`OUT-*`) — sin cambios respecto a v1
`OUT-REP` · `OUT-BRIEF` · `OUT-TABLE` · `OUT-DASH` · `OUT-CHK` · `OUT-ALERT` · `OUT-DOC` ·
`OUT-EMAIL` · `OUT-PACK` · `OUT-REC` · `OUT-BIT` · `OUT-SCORE`

> Nota: `OUT-EMAIL` significa **redactar**, no enviar. Enviar es `ACT-EMAIL-S`.

### 4.5 Acción (`ACT-*`) — **nueva categoría, corrige E1**

| Código | Acción | Control mínimo |
|---|---|---|
| `ACT-ERP-W` | Escritura en el ERP | Whitelist de entidades + bitácora |
| `ACT-EMAIL-S` | Envío real de correo/mensaje | `CTL-HITL` si es externo y no es plantilla |
| `ACT-DOC-S` | Emisión de documento oficial (CFDI, Carta Porte) | `CTL-HITL` siempre |
| `ACT-PAY` | Instrucción de pago | `CTL-HITL` siempre + doble factor |
| `ACT-NOTIFY` | Notificación interna | Libre |

**Regla dura: ningún agente tiene `ACT-*` por defecto.** Se otorga agente por agente, con umbral.

### 4.6 Control (`CTL-*`) — corregido

| Código | Habilidad | Cambio |
|---|---|---|
| `CTL-ESC` | Escalamiento: notifica a un humano y **sigue trabajando** | Diferenciado |
| `CTL-HITL` | Bloqueo: **se detiene** hasta aprobación humana | Diferenciado |
| `CTL-LIMIT` | Umbrales numéricos duros | Ahora parametrizado (§6.2) |
| `CTL-AUDIT` | Bitácora inmutable | — |
| `CTL-REJECT` | Devolución por error | — |
| `CTL-CONF` | Nivel de certeza y supuestos explícitos | — |
| `CTL-VERSION` | Versionado | — |
| `CTL-POLICY` | Cumplimiento de política interna | **Ahora sí asignado** (Compliance + gate) |

---

## 5. Los 29 servicios determinísticos (Python, cero tokens)

### Capa de datos — prerrequisito
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-masterdata` | *(hueco)* | Catálogo único: clientes, unidades, operadores, rutas, tarifas |
| `svc-ingest` | *(hueco)* | Normalización de bancos, tickets de diesel, GPS, CSV del ERP |

### Finanzas
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-costing` | A10 | Costo por km y por viaje: diesel, casetas, operador, mantenimiento, llantas, seguro, depreciación, fijos asignados |
| `svc-profitability` | A11 | Margen por viaje, ruta, cliente, unidad, operador |
| `svc-scenarios` | A12 | Sensibilidad, punto de equilibrio, escenarios min/objetivo/óptimo |
| `svc-financials` | A7, A8 | EEFF, EBITDA, ROIC, liquidez, variaciones vs presupuesto |
| `svc-treasury` | A14 | Posición de caja, flujo diario y semanal, días de caja |
| `svc-ar` | A15 | Aging de cartera, riesgo de morosidad, flujo esperado |
| `svc-ap` | A16 | Calendario de pagos, vencimientos, priorización |
| `svc-invoicing` | *(hueco)* | Emisión y timbrado, incluye demoras/estadías |
| `svc-cfdi-validate` | A18, A74 | **Validación XSD + reglas SAT de Carta Porte y CFDI.** Un LLM aquí sólo añade riesgo en un documento fiscal |

### Operaciones
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-routing` | A21 | Distancia, ETA, casetas — vía API de ruteo, no vía modelo |
| `svc-capacity` | A22 | Asignación unidad-operador-viaje como problema de restricciones |
| `svc-telemetry` | A24, A34 | Geocercas, desvíos, paradas no autorizadas, retrasos. Corre 24/7 |
| `svc-fleet-docs` | A27, A73 | Vigencias de pólizas, permisos, verificaciones — aritmética de fechas |
| `svc-maintenance` | A28 | Disparadores de servicio por kilometraje y horas |
| `svc-fuel` | A29 | km/litro, consumo esperado vs real, detección estadística de anomalías |
| `svc-doc-checklist` | A32 | Completitud documental del viaje antes de facturar |
| `svc-emissions` | A95 | Emisiones = factor × litros |

### Comercial
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-pricing` | A38 | Tarifa = `svc-costing` + margen objetivo + política de descuento |

### Talento
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-payroll` | A85, A86, A87 | Pre-nómina, bonos, validación de incidencias |

### Transversales
| Servicio | Reemplaza | Función |
|---|---|---|
| `svc-kpi` | A4 | Indicadores globales y por departamento |
| `svc-alerts` | A5 | Motor de reglas sobre umbrales — liquidez, margen, vencimientos, desvíos |
| `svc-validation` | A9, A13, A40, A57, A87, A92 | **QA transversal**: reglas por dominio |
| `svc-trace` | A98 | Reconciliación cifra ↔ consulta origen. Bloquea entregables que no cuadran |
| `svc-audit` | A78, A79, A80 | Auditoría continua por cruce de datos |
| `svc-rbac` | A56, A67 | Matriz de roles y permisos |
| `svc-privacy` | *(hueco)* | Clasificación y redacción de PII, retención |
| `svc-budget` | *(hueco)* | Presupuesto de tokens por agente y alerta de sobregiro |
| `svc-notify` | A26 (parcial) | Plantillas fijas de aviso a cliente y operador, sin LLM |

**Infraestructura estándar** (no son servicios de negocio, son herramientas de mercado):
CI/CD → GitHub Actions · Monitoreo → Sentry/Grafana · Dashboards → Metabase ·
Workflows → n8n o Temporal · Backups → cron. Esto sustituye a A58, A59, A62, A63, A68.

---

## 6. Los 33 agentes IA

### D1 · Dirección y Gobierno — 3 agentes *(era 5 + líder)*

| ID | Agente | Absorbe | Nivel |
|---|---|---|---|
| `D1-01` | Estrategia y Decisión Ejecutiva | A1 | Alto |
| `D1-02` | Gobierno Corporativo y PMO | A2 | Medio |
| `D1-03` | Síntesis Ejecutiva | A3, narración de A4/A5 | Bajo |

`D1-03` se separa de `D1-01` a propósito: el daily brief es de alta frecuencia y va en modelo
barato; la estrategia es de baja frecuencia y va en modelo caro. Fusionarlos obligaría a pagar el
modelo caro todos los días.

### D2 · Finanzas y Administración — 6 agentes *(era 14 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D2-01` | Controller Financiero | A7, A8, A9 | `svc-financials`, `svc-validation` |
| `D2-02` | FP&A y Escenarios | A6, A12 | `svc-scenarios`, `svc-financials` |
| `D2-03` | Costos y Márgenes | A10, A11, A13 | `svc-costing`, `svc-profitability` |
| `D2-04` | Ciclo de Ingreso: Facturación y Cobranza | A15 + *hueco facturación* | `svc-invoicing`, `svc-ar`, `svc-cfdi-validate` |
| `D2-05` | Ciclo de Egreso: CXP y Proveedores | A16 + *hueco compras* | `svc-ap`, `svc-treasury` |
| `D2-06` | Contabilidad, Fiscal y Documental | A17, A18, A19 | `svc-cfdi-validate`, `svc-doc-checklist` |

### D3 · Operaciones Logísticas — 6 agentes *(era 16 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D3-01` | Planeación y Programación | A20, A21, A22 | `svc-routing`, `svc-capacity` |
| `D3-02` | Dispatch y Torre de Control | A23, A24, A26 | `svc-telemetry`, `svc-notify` |
| `D3-03` | Incidencias y Eventos Críticos | A25, A35 | `svc-alerts` |
| `D3-04` | Flota, Mantenimiento y Combustible | A27, A28, A29 | `svc-fleet-docs`, `svc-maintenance`, `svc-fuel` |
| `D3-05` | Evidencias y Cierre de Viaje | A30, A31, A32 | `svc-doc-checklist` |
| `D3-06` | Seguridad y Riesgo en Ruta | A33, A34 | `svc-telemetry` |

`D3-02` no monitorea: `svc-telemetry` monitorea 24/7 en código y el agente **sólo se activa ante
excepción**. Esto resuelve el problema de cobertura continua sin pagar tokens en reposo.

### D4 · Comercial y Cliente — 5 agentes *(era 11 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D4-01` | Prospección e Inteligencia Comercial | A36 | — |
| `D4-02` | Pipeline y Seguimiento | A37 | `svc-kpi` |
| `D4-03` | Pricing y Propuestas | A38, A39, A40 | `svc-pricing`, `svc-costing`, `svc-validation` |
| `D4-04` | Atención y Customer Success | A41, A42, A43 | `svc-kpi` |
| `D4-05` | Marketing y Contenido | A44, A45, A46 | — |

En `D4-03` el precio lo produce `svc-pricing`; el agente sólo redacta la propuesta y argumenta.
El gate de margen mínimo es determinístico: **una cotización con margen bajo el umbral no puede
generarse**, no depende de que el LLM lo note.

### D5 · Tecnología y Datos — 3 agentes *(era 22 + líder)*

| ID | Agente | Absorbe |
|---|---|---|
| `D5-01` | Producto y Requerimientos ERP | A47, A48, A49 |
| `D5-02` | Datos e Insights | A61 |
| `D5-03` | AgentOps: Arquitectura y Calidad de Agentes | A64, A65, A97, A98, A99 |

**A50–A60 desaparecen como agentes.** UX, frontend, backend, base de datos, APIs, QA técnico,
DevOps y documentación técnica son trabajo de ingeniería asistido con Claude Code sobre el repo del
ERP — no plazas de una oficina virtual. A66/A67/A68 pasan a `svc-rbac` y herramientas estándar.

### D6 · Legal, Compliance y Riesgos — 4 agentes *(era 13 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D6-01` | Legal Corporativo y Contratos | A69, A70, A71 | — |
| `D6-02` | Compliance y Permisos | A72, A73, A74 | `svc-fleet-docs`, `svc-cfdi-validate` |
| `D6-03` | Riesgos, Seguros y Siniestros | A75, A76, A77 | — |
| `D6-04` | Auditoría Interna | A78, A79, A80, A81 | `svc-audit`, `svc-trace` |

`D6-04` no busca hallazgos: `svc-audit` los encuentra por cruce de datos y el agente los redacta,
prioriza y da seguimiento.

### D7 · Talento y Cultura — 3 agentes *(era 9 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D7-01` | Reclutamiento y Onboarding | A82, A83, A84 | `svc-privacy` |
| `D7-02` | Nómina y Compensaciones | A85, A86, A87 | `svc-payroll`, `svc-validation` |
| `D7-03` | Capacitación, Cultura y Desempeño | A88, A89, A90 | — |

`D7-01` **extrae** datos de CVs; **no puntúa candidatos**. La rúbrica de scoring es determinística
y versionada, con atributos protegidos excluidos por lista (corrige R3).

### D8 · Calidad, Procesos y Sostenibilidad — 2 agentes *(era 9 + líder)*

| ID | Agente | Absorbe | Servicios |
|---|---|---|---|
| `D8-01` | Procesos, SOPs y Mejora Continua | A91, A92, A93 | `svc-validation` |
| `D8-02` | ESG, Seguridad e Higiene | A94, A95, A96 | `svc-emissions` |

### Orquestador — 1 agente

`O1` mantiene su misión, pero **deja de enrutar por LLM en los casos conocidos**: el ruteo de
solicitudes recurrentes es una tabla. El modelo sólo interviene ante solicitudes nuevas o
ambiguas, y ante integración de entregables multidominio.

---

## 6.2 Tabla de umbrales — hace implementable `CTL-LIMIT` (corrige E5)

Valores por defecto propuestos. **Deben calibrarse con tus cifras reales antes de encender nada.**

| Decisión | Agente decide solo | Humano operativo | Dirección |
|---|---|---|---|
| Pago a proveedor | ≤ $5,000 MXN con OC previa y proveedor registrado | $5,000 – $100,000 | > $100,000 |
| Descuento sobre tarifa | ≤ 3% | 3% – 8% | > 8% |
| Cotización | Margen ≥ objetivo y desviación ≤ 5% | Margen entre mínimo y objetivo | Margen < mínimo |
| Cobranza | Recordatorio con plantilla, ≤ 15 días vencido | 15 – 60 días | > 60 días o vía legal |
| Compromiso de viaje | Unidad y operador disponibles y documentos vigentes | Cualquier restricción incumplida | — |
| Incidencia en ruta | Severidad 1–2: registra y notifica | Severidad 3 | Severidad 4–5 (robo, accidente) |
| Emisión de CFDI | Nunca | Siempre revisa | — |
| Contratación / baja | Nunca | Prepara expediente | Autoriza |
| Contrato con cliente | Nunca | Redacta y marca riesgos | Firma |

**`CTL-ESC` vs `CTL-HITL`:** `ESC` notifica y el agente continúa. `HITL` detiene el flujo hasta
aprobación registrada. Toda `ACT-PAY` y `ACT-DOC-S` es `HITL`. Toda `ACT-EMAIL-S` externa es
`HITL` salvo plantilla fija de `svc-notify`.

## 6.3 Escalonamiento de modelo — gobierno de costo (corrige R4)

| Nivel | Uso | Agentes |
|---|---|---|
| **Alto** | Juicio complejo, baja frecuencia | `D1-01`, `D6-01`, `D6-03`, `D5-03` |
| **Medio** | Operación diaria con criterio | mayoría de agentes de D2, D3, D4, D6, D7, D8 |
| **Bajo** | Clasificación, resumen, plantillas, alta frecuencia | `D1-03`, `D3-02`, `D4-02`, `D4-04` |
| **Código** | Costo cero | los 29 servicios |

`svc-budget` impone un tope mensual por agente y alerta al 80%.

---

## 7. Flujo operativo corregido

En v1 todo entregable pasaba por 4 capas. En v2 el circuito depende de la **criticidad**:

```
Solicitud
   │
   ├─ ¿Es recurrente y conocida? ──► ruteo por tabla (sin LLM)
   │                                       │
   └─ ¿Es nueva o ambigua? ──► Orquestador ┘
                                           │
                                 Agente de dominio
                                           │
                              invoca servicios determinísticos
                                           │
                                svc-validation + svc-trace
                                     │            │
                              ¿pasa? ─┴─ no ──► corrige y reintenta (máx. 2)
                                     │
                                    sí
                                     │
                    ┌────────────────┴────────────────┐
              Criticidad baja                  Criticidad alta
                    │                                 │
             Entrega directa                  Gate de Autoridad (§6.2)
                                                      │
                                              Humano autoriza
                                                      │
                                             Entrega + bitácora
```

**Criticidad alta** = tiene `ACT-*` con efecto externo, o supera un umbral de §6.2, o es un
documento fiscal/legal. Todo lo demás es criticidad baja y se entrega sin gate.

Esto baja el promedio de **4–6 llamadas LLM por entregable a 1–2**.

---

## 8. Plan de implementación por fases

El error más caro sería construir 33 agentes antes de que uno solo demuestre retorno.

### Fase 0 — Fundación de datos *(semanas 1–3, cero IA)*
`svc-masterdata` · `svc-ingest` · `svc-costing` · `svc-profitability`

Sin un solo agente ya obtienes **costo por km y margen real por viaje, ruta y cliente**. Para una
transportista en arranque, este suele ser el mayor retorno individual de todo el proyecto — y es
100% código, testeable, sin riesgo de alucinación.

### Fase 1 — Cotizar sin perder margen *(semanas 4–7)*
`svc-pricing` · `svc-validation` · **`D4-03` Pricing y Propuestas** · **`D2-03` Costos y Márgenes**

Primeros 2 agentes. Precio calculado en Python, propuesta redactada por IA, gate de margen mínimo
determinístico.

### Fase 2 — Cerrar el ciclo operación → ingreso *(semanas 8–11)*
`svc-doc-checklist` · `svc-invoicing` · `svc-cfdi-validate` ·
**`D3-05` Evidencias y Cierre** · **`D2-04` Ciclo de Ingreso**

Cierra el hueco de facturación. Acelera el ciclo de cobro, que es lo que sostiene el flujo.

### Fase 3 — Visibilidad y control *(semanas 12–16)*
`svc-treasury` · `svc-ar` · `svc-ap` · `svc-kpi` · `svc-alerts` · `svc-trace` ·
**`D1-03` Síntesis Ejecutiva**

Daily brief y alertas de liquidez con datos verificados.

### Fase 4 — Operación en tiempo real *(mes 5+)*
`svc-telemetry` · `svc-routing` · `svc-capacity` · `svc-fleet-docs` · `svc-maintenance` ·
`svc-fuel` · **`D3-01`, `D3-02`, `D3-04`**

### Fase 5+ — El resto, sólo bajo demanda real
Legal, Talento, Calidad, ESG, Marketing. Ninguno se enciende sin un caso de uso que lo pida.

**MVP = 5 agentes IA + 8 servicios**, no 108 agentes.

---

## 9. Estructura propuesta del repositorio

```
AI-company/
├── docs/
│   ├── arquitectura-v2.md          ← este documento
│   ├── catalogo-habilidades.md
│   └── umbrales.md                 ← §6.2, calibrable
├── registry/
│   ├── agents/                     ← 33 definiciones YAML
│   └── services/                   ← 29 contratos de servicio
├── services/                       ← Python determinístico
│   ├── masterdata/
│   ├── costing/
│   ├── pricing/
│   └── ...
├── agents/                         ← prompts + binding de herramientas
├── tests/                          ← pytest sobre cada servicio
└── scripts/
    └── validate_registry.py        ← detecta los errores tipo §1.1 automáticamente
```

`validate_registry.py` verifica que ninguna habilidad referenciada exista fuera del catálogo,
que ningún agente tenga `ACT-*` sin control asociado, y que ninguna capacidad quede huérfana.
Los 7 errores de §1.1 se habrían detectado solos.

---

## 10. Lo que cambia para ti en la práctica

| Antes | Después |
|---|---|
| El costo por km depende de qué agente lo calcule | Un solo servicio, un solo número, con test |
| Un error de cálculo del LLM llega a una cotización | Imposible: el LLM no calcula |
| 108 agentes por mantener y presupuestar | 33 agentes + 29 funciones Python |
| Todo entregable pasa por 4 revisiones | Sólo lo crítico |
| Un agente podía escribir a un cliente sin filtro | Comunicación externa con HITL o plantilla fija |
| Sin política de datos personales | `svc-privacy` con redacción y retención |
| Arranque de golpe | 4 servicios en 3 semanas que ya dan margen real |
