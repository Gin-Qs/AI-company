# Oficina Virtual de Agentes IA — Arquitectura v3

> **Arquitectura vigente.** Sustituye a `arquitectura-v2.md`, que queda como histórico.
>
> **Capa organizacional:** 8 departamentos · 42 equipos
> **Capa ejecutable:** 1 orquestador + 32 agentes de dominio = **33 agentes IA**
> **Capa determinística:** **31 servicios Python**
> **Capa de control:** Gate de Autoridad · RBAC · HITL · `ACT-*` · bitácora · privacidad · presupuesto

---

## 0. Qué es la v3 y qué resuelve

La v1 diseñó la empresa (108 agentes LLM). La v2 diseñó el motor (33 agentes + servicios
determinísticos) pero borró la empresa. **La v3 conserva las dos capas y las mantiene separadas:**

> La empresa se organiza como corporativo.
> Los procesos se ejecutan como software.
> Los agentes razonan, redactan y coordinan.
> Los servicios calculan, validan y accionan.
> Los humanos autorizan lo crítico.

La distinción de fondo:

```
estructura organizacional  ≠  estructura ejecutable
     (cuesta cero tokens)      (cuesta tokens y se audita)
```

Tener 8 departamentos y 42 equipos no obliga a tener 42 agentes. Los equipos existen para
*ownership*, permisos, presupuesto, KPIs, carpetas, escalamiento y crecimiento futuro. Sólo la
capa ejecutable consume modelo.

**La v3 no cambia el motor de la v2.** Los 33 agentes, sus IDs y sus fusiones son idénticos y ya
fueron auditados en `arquitectura-v2.md §1`. Lo que la v3 añade es el marco de gobierno alrededor
del motor: capa organizacional, trazabilidad de proceso, contrato de comunicación con personas y
regla general de rúbricas contra sesgo.

### 0.1 Objetivos rectores

Toda decisión de este documento se justifica contra uno de estos cuatro objetivos:

| # | Objetivo | Dónde se materializa |
|---|---|---|
| **O1** | Optimizar y facilitar el trabajo | §3 (LLM vs. servicios), §11 (roadmap por retorno) |
| **O2** | Reducir sesgos | §9 (rúbricas y sesgo), §8.4 (privacidad) |
| **O3** | Mejorar la comunicación agente↔persona | §7 (contrato de entregable, bandeja HITL) |
| **O4** | Trazar el camino y el progreso de cada agente | §8 (`svc-runlog`, estado de caso) |

---

## 1. Comparativo v1 · v2 · v3

| Elemento | v1 | v2 | **v3 (vigente)** |
|---|---|---|---|
| Departamentos | 8 | 8 dominios | **8 departamentos** |
| Equipos | 31 (declarados) | eliminados como capa | **42 equipos con owner** |
| Agentes IA | 108 | 33 | **33** (sin cambio) |
| Servicios determinísticos | 0 | 30 (rotulados "29") | **31** |
| Líderes de departamento | 8 agentes LLM | eliminados | **8 roles de gobierno, sin llamada LLM** |
| QA | 9 agentes QA | `svc-validation` | `svc-validation` + muestreo humano |
| Cálculos | LLM | Python | Python |
| Ruteo | Agentes/líderes | Tabla + orquestador | Tabla + orquestador + política de criticidad |
| Acción real | indefinida | `ACT-*` | `ACT-*` con umbral, permiso y bitácora |
| Trazabilidad | ninguna | de cifras (`svc-trace`) | **de cifras + de proceso (`svc-runlog`)** |
| Comunicación con humanos | implícita | implícita | **contrato de entregable + bandeja HITL con SLA** |
| Antisesgo | ausente | scoring de personas | **rúbrica versionada para todo ranking con consecuencia** |

### 1.1 Correcciones de conteo respecto a documentos previos

Se corrigen aquí dos cifras que circulaban mal:

1. **Los equipos son 42, no 31.** La v1 declaraba 31 y los borradores de la v3 repetían el número
   por inercia, pero el desglose por departamento suma 42 (§4). Se adopta 42. El número de equipos
   no es una propiedad de la arquitectura; la cobertura sí.
2. **Los servicios eran 30, no 29.** El rótulo "29 servicios" de la v2 era un error aritmético: su
   propio catálogo (`arquitectura-v2.md §5`) lista 30 entradas. **No se fusiona `svc-alerts` con
   `svc-notify` para cuadrar el número** — son responsabilidades distintas (motor de reglas vs.
   plantillas de comunicación) y fusionarlas por estética numérica produciría un servicio con dos
   razones para cambiar. Con `svc-runlog` (§8.1), el catálogo v3 queda en **31**.

---

## 2. Principios

1. **Determinismo primero.** Si se puede calcular, se calcula. El LLM es el último recurso.
2. **Una sola fuente de verdad por número.** Un solo `svc-costing`. Un solo `svc-pricing`.
3. **Ningún agente afirma una cifra que no venga de una herramienta.** `svc-trace` lo verifica.
4. **Toda acción con efecto externo requiere autorización explícita y registrada.**
5. **Un agente por proceso de negocio, no por tarea.** Las tareas son herramientas.
6. **Los equipos son organización; los agentes son ejecución.** Los equipos no cuestan tokens.
7. **Los líderes son gobierno, no una llamada obligatoria.**
8. **Todo caso deja rastro.** Si no quedó en `svc-runlog`, no ocurrió.
9. **Todo ranking con consecuencia sale de una rúbrica versionada,** no del criterio del modelo.
10. **Ningún agente se enciende sin retorno medible.** Fases, no big bang.

---

## 3. La regla central: qué hace cada capa

### 3.1 El LLM sí hace

Interpretar solicitudes · clasificar casos ambiguos · extraer información de texto no estructurado ·
redactar propuestas, reportes y comunicados · resumir · explicar resultados · priorizar con contexto
de negocio · análisis cualitativo · recomendar · coordinar agentes y servicios · preparar decisiones
humanas.

### 3.2 El LLM no hace

Calcular costo por km · calcular margen · validar CFDI · calcular nómina · producir el score
numérico final · detectar anomalías estadísticas · emitir facturas · autorizar pagos · escribir en
el ERP sin permiso · enviar comunicación externa sin control · ser juez y parte en QA · afirmar
cifras sin fuente · **elegir qué entra a un brief ejecutivo** (§9.2).

### 3.3 Los servicios determinísticos hacen

Cálculos · comparaciones · validaciones · simulaciones · scoring con rúbrica · reconciliación ·
auditoría · alertas · registro de proceso · escritura controlada en sistemas · acciones repetibles.

---

## 4. Capa organizacional — 8 departamentos, 42 equipos

Cada equipo existe en `registry/teams/*.yaml` y **debe declarar owner humano, owner digital y
agentes asociados**. Un equipo sin agente es válido; un equipo sin owner no lo es, y
`validate_registry.py` lo rechaza (§10.3).

| # | Departamento | Equipos | Agentes |
|---|---|---|---|
| 01 | Dirección y Gobierno | 3 | 3 |
| 02 | Finanzas, Contabilidad y Administración | 6 | 6 |
| 03 | Operaciones Logísticas | 7 | 6 |
| 04 | Comercial y Cliente | 5 | 5 |
| 05 | Tecnología, Datos e Innovación | 6 | 3 |
| 06 | Legal, Compliance y Riesgos | 5 | 4 |
| 07 | Talento y Cultura | 5 | 3 |
| 08 | Calidad, Procesos y Sostenibilidad | 5 | 2 |
| | **Total** | **42** | **32 + O1 = 33** |

### 4.1 Mapa equipo → agente

Donde no hay agente, la columna dice **con qué se cubre**. Esto evita equipos fantasma.

**01 · Dirección y Gobierno**

| Equipo | Agente / cobertura |
|---|---|
| Estrategia Corporativa | `D1-01` |
| Gobierno Corporativo y PMO | `D1-02` |
| Inteligencia Ejecutiva y KPIs Globales | `D1-03` + `svc-kpi` |

**02 · Finanzas, Contabilidad y Administración**

| Equipo | Agente / cobertura |
|---|---|
| Planeación y Análisis Financiero | `D2-02` |
| Costos y Rentabilidad Logística | `D2-03` |
| Tesorería y Liquidez | `D2-01` + `svc-treasury` |
| Ciclo de Ingreso: Facturación y Cobranza | `D2-04` |
| Ciclo de Egreso: CXP, Compras y Proveedores | `D2-05` |
| Contabilidad, Fiscal y Administración Documental | `D2-06` |

**03 · Operaciones Logísticas**

| Equipo | Agente / cobertura |
|---|---|
| Planeación, Rutas y Programación | `D3-01` |
| Tráfico y Dispatch | `D3-02` |
| Torre de Control | `D3-02` + `svc-telemetry` (el servicio corre 24/7; el agente sólo ante excepción) |
| Incidencias y Eventos Críticos | `D3-03` |
| Flota, Mantenimiento y Combustible | `D3-04` |
| Evidencias y Cierre de Viaje | `D3-05` |
| Seguridad Operativa y Riesgo en Ruta | `D3-06` |

**04 · Comercial y Cliente**

| Equipo | Agente / cobertura |
|---|---|
| Prospección e Inteligencia Comercial | `D4-01` |
| CRM, Pipeline y Seguimiento | `D4-02` |
| Pricing, Cotizaciones y Propuestas | `D4-03` |
| Atención y Customer Success | `D4-04` |
| Marketing, Marca y Contenido | `D4-05` |

**05 · Tecnología, Datos e Innovación**

| Equipo | Agente / cobertura |
|---|---|
| Producto ERP y Requerimientos | `D5-01` |
| Arquitectura Técnica y Desarrollo | **Sin agente.** Ingeniería humana asistida con Claude Code sobre el repo del ERP |
| Data, BI e Insights | `D5-02` + Metabase |
| AgentOps y Calidad IA | `D5-03` |
| Automatización e Integraciones | **Sin agente.** n8n o Temporal |
| IT, Seguridad y Continuidad | **Sin agente.** `svc-rbac` + herramientas estándar (§6.6) |

**06 · Legal, Compliance y Riesgos**

| Equipo | Agente / cobertura |
|---|---|
| Legal Corporativo y Contratos | `D6-01` |
| Compliance y Permisos | `D6-02` |
| Riesgos Empresariales | `D6-03` |
| Seguros y Siniestros | `D6-03` |
| Auditoría Interna y Control | `D6-04` + `svc-audit` |

**07 · Talento y Cultura**

| Equipo | Agente / cobertura |
|---|---|
| Reclutamiento y Onboarding | `D7-01` |
| Expedientes Laborales | `D7-01` + `svc-privacy` |
| Nómina y Compensaciones | `D7-02` |
| Capacitación y Manuales | `D7-03` |
| Cultura, Clima y Desempeño | `D7-03` |

**08 · Calidad, Procesos y Sostenibilidad**

| Equipo | Agente / cobertura |
|---|---|
| Procesos y SOPs | `D8-01` |
| Calidad Operativa | `D8-01` + `svc-validation` |
| Mejora Continua | `D8-01` |
| ESG y Sostenibilidad | `D8-02` + `svc-emissions` |
| Seguridad e Higiene | `D8-02` |

### 4.2 Líderes de departamento

| | Rol del líder |
|---|---|
| v1 | Agente LLM activo — 8 llamadas al modelo sólo para enrutar |
| v2 | Eliminado |
| **v3** | **Rol de gobierno: owner humano + owner digital + políticas + KPIs + umbrales + rutas de escalamiento + configuración de ruteo** |

El líder existe como configuración y como dashboard, **no como llamada LLM en cada flujo**. La capa
se reinstala como agente sólo si un dominio supera ~8 agentes; hoy ninguno lo hace.

### 4.3 Propiedad compartida — cómo se declara el owner

El organigrama de Fleeter está diseñado a propósito como **estructura conjunta**: 4 personas
cubren 42 equipos repartiéndose la carga, y la mayoría de las funciones son explícitamente
compartidas. La arquitectura respeta eso y no lo aplana. Cada equipo declara dos campos:

| Campo | Qué significa |
|---|---|
| `owner_humano` | **Responsable único.** A quién se le enruta un HITL de este equipo y quién responde por el resultado. Uno solo, siempre |
| `co_owners` | **Carga compartida real.** Ven la bandeja del equipo y pueden actuar sobre ella |

La distinción no es burocrática, es lo que hace funcionar el Gate: **una solicitud de aprobación
necesita un destinatario por defecto, o no llega a nadie.** Compartir el trabajo es la forma de
operar; compartir la responsabilidad de una aprobación es cómo un HITL vence sin que nadie se
entere de que era suyo. `co_owners` conserva lo primero sin caer en lo segundo.

De los 42 equipos, **28 tienen carga compartida declarada**. La distribución de responsabilidad
única es: Gabriel 22, Elias 9, Nay 8, Ana 3 — ver `docs/owners-equipos.csv` y `registry/teams/`.

> **Riesgo estructural declarado:** más de la mitad de los equipos tienen a Gabriel como
> responsable único, y él es también quien aprueba todo lo que sale de rango en el Gate. La
> bandeja de HITL va a converger en una sola persona. No es un error del modelo — es el
> organigrama real — pero sí es la primera métrica a vigilar en `svc-runlog`: si la tasa de
> expiración de HITL de Dirección sube, el cuello de botella es de agenda, no de umbral.

---

## 5. Capa ejecutable — 33 agentes

**Dónde vive el detalle.** Este documento define, por agente: misión, qué absorbe de la v1, límites
duros, servicios y nivel de modelo. **Las entradas, salidas, herramientas, prompts y controles
formales viven en `registry/agents/*.yaml`** (§10.1) y son la fuente de verdad ejecutable.
Duplicarlos aquí violaría el principio 2.

Los "límites duros" no son adorno: cada uno se traduce en una validación del registro o en una
regla del Gate.

### D1 · Dirección y Gobierno — 3 agentes *(v1: 5 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D1-01` | Estrategia y Decisión Ejecutiva | A1 | `svc-kpi`, `svc-alerts`, `svc-budget`, `svc-trace` | Alto |
| `D1-02` | Gobierno Corporativo y PMO | A2 | `svc-kpi`, `svc-alerts`, `svc-audit` | Medio |
| `D1-03` | Síntesis Ejecutiva | A3, narración de A4/A5 | `svc-kpi`, `svc-alerts`, `svc-trace` | Bajo |

**Límites duros**
- `D1-01` no decide estrategia, no aprueba inversiones, no firma acuerdos.
- `D1-02` no cambia prioridades ni aprueba presupuesto de proyecto sin autorización.
- `D1-03` no genera números propios y **no elige qué entra al brief**: la selección la hace
  `svc-alerts` (§9.2). El agente narra lo seleccionado.

`D1-03` se separa de `D1-01` a propósito: el daily brief es de alta frecuencia y va en modelo
barato; la estrategia es de baja frecuencia y va en modelo caro.

### D2 · Finanzas, Contabilidad y Administración — 6 agentes *(v1: 14 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D2-01` | Controller Financiero | A7, A8, A9, A14 | `svc-financials`, `svc-validation`, `svc-trace`, `svc-kpi` | Medio |
| `D2-02` | FP&A y Escenarios | A6, A12 | `svc-scenarios`, `svc-financials`, `svc-budget` | Medio |
| `D2-03` | Costos y Márgenes | A10, A11, A13 | `svc-costing`, `svc-profitability`, `svc-scenarios`, `svc-trace` | Medio |
| `D2-04` | Ciclo de Ingreso: Facturación y Cobranza | A15 + *hueco facturación* | `svc-invoicing`, `svc-ar`, `svc-cfdi-validate`, `svc-doc-checklist`, `svc-notify` | Medio |
| `D2-05` | Ciclo de Egreso: CXP, Compras y Proveedores | A16 + *hueco compras* | `svc-ap`, `svc-treasury`, `svc-validation`, `svc-budget` | Medio |
| `D2-06` | Contabilidad, Fiscal y Documental | A17, A18, A19 | `svc-cfdi-validate`, `svc-doc-checklist`, `svc-privacy` | Medio |

**Límites duros**
- Ninguno calcula ratios, escenarios, costo por km ni márgenes: los produce el servicio.
- `D2-03` **no duplica costeo comercial** — `D4-03` consume el mismo `svc-costing` (corrige el
  error más grave de la v1: dos números distintos para la misma ruta).
- `D2-04` no emite CFDI sin `CTL-HITL`, no envía cobranza externa fuera de plantilla, no modifica montos.
- `D2-05` no ejecuta pagos sin autorización ni aprueba proveedor crítico.
- `D2-06` no presenta declaraciones ni da opinión fiscal final.

### D3 · Operaciones Logísticas — 6 agentes *(v1: 16 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D3-01` | Planeación y Programación | A20, A21, A22 | `svc-routing`, `svc-capacity`, `svc-fleet-docs`, `svc-alerts` | Medio |
| `D3-02` | Dispatch y Torre de Control | A23, A24, A26 | `svc-telemetry`, `svc-notify`, `svc-alerts` | Bajo |
| `D3-03` | Incidencias y Eventos Críticos | A25, A35 | `svc-alerts`, `svc-trace`, `svc-audit`, `svc-notify` | Medio |
| `D3-04` | Flota, Mantenimiento y Combustible | A27, A28, A29 | `svc-fleet-docs`, `svc-maintenance`, `svc-fuel`, `svc-alerts` | Medio |
| `D3-05` | Evidencias y Cierre de Viaje | A30, A31, A32 | `svc-doc-checklist`, `svc-validation`, `svc-trace` | Medio |
| `D3-06` | Seguridad y Riesgo en Ruta | A33, A34 | `svc-telemetry`, `svc-routing`, `svc-alerts` | Medio |

**Límites duros**
- `D3-01` no inventa rutas, no asigna unidad con documentos vencidos, no compromete viajes inviables.
  **La asignación unidad-operador sale de `svc-capacity` como problema de restricciones, no del modelo** (§9.1).
- `D3-02` **no monitorea**: `svc-telemetry` corre 24/7 en código y el agente se activa sólo ante
  excepción. Esto cubre 24/7 sin pagar tokens en reposo. No envía mensajes externos libres.
- `D3-03` no oculta incidentes, no decide en siniestros severos, no comunica crisis externa sin humano.
- `D3-04` no calcula anomalías de combustible (lo hace `svc-fuel`) ni autoriza reparación costosa.
- `D3-05` no factura, no libera cierre con faltantes, no modifica evidencia.
- `D3-06` no sustituye seguridad humana ni decide rutas de alto riesgo sin autorización.

### D4 · Comercial y Cliente — 5 agentes *(v1: 11 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D4-01` | Prospección e Inteligencia Comercial | A36 | `svc-privacy`, `svc-budget` | Medio |
| `D4-02` | Pipeline y Seguimiento | A37 | `svc-kpi`, `svc-notify`, `svc-alerts` | Bajo |
| `D4-03` | Pricing y Propuestas | A38, A39, A40 | `svc-pricing`, `svc-costing`, `svc-profitability`, `svc-validation`, `svc-trace` | Medio |
| `D4-04` | Atención y Customer Success | A41, A42, A43 | `svc-kpi`, `svc-alerts`, `svc-notify` | Bajo |
| `D4-05` | Marketing y Contenido | A44, A45, A46 | `svc-kpi`, `svc-budget` | Bajo |

**Límites duros**
- `D4-01` no compra bases ilegales, no contacta sin control y **no puntúa prospectos con el modelo**:
  el score sale de rúbrica versionada (§9.1).
- `D4-02` no promete condiciones comerciales, no envía correo externo libre, no modifica CRM sin permiso.
- `D4-03` **no calcula el precio.** El gate de margen mínimo es determinístico: una cotización bajo
  el umbral **no puede generarse**, no depende de que el LLM lo note.
- `D4-04` no acepta reclamaciones económicas ni promete compensaciones.
- `D4-05` no publica sin aprobación ni promete capacidades inexistentes.

### D5 · Tecnología, Datos e Innovación — 3 agentes *(v1: 22 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D5-01` | Producto y Requerimientos ERP | A47, A48, A49 | `svc-kpi`, `svc-validation`, `svc-budget` | Medio |
| `D5-02` | Datos e Insights | A61 | `svc-kpi`, `svc-trace`, `svc-alerts`, `svc-audit` | Medio |
| `D5-03` | AgentOps: Arquitectura y Calidad de Agentes | A64, A65, A97, A98, A99 | `svc-validation`, `svc-trace`, `svc-runlog`, `svc-budget`, `svc-privacy`, `svc-rbac` | Alto |

**A62 y A63 tampoco son agentes:** dashboards es Metabase sobre `svc-kpi` (equipo Data, BI e
Insights) y automatización es n8n o Temporal (equipo Automatización e Integraciones). Ambos
aparecen en §4.1 como cobertura sin agente.

**A50–A60 no son plazas de la oficina virtual.** UX, frontend, backend, base de datos, APIs, QA
técnico, DevOps y documentación técnica no son operación de una transportista: son proyecto. Pero
tampoco desaparecen — **vuelven como capa de consultoría `C-01`…`C-09` (§5-bis)**, invocables por
Dirección o `D5-01` cuando el ERP los necesite, sin `ACT-*` y sin estar encendidos nunca.
`A66` pasa a `svc-rbac` y herramientas estándar; `A67` y `A68` entran en `C-06` y `C-08`.

`D5` es el departamento que construye el ERP junto con Dirección y esa capa de consultoría.

**Límites duros**
- `D5-02` no calcula KPIs ni valida cifras sin `svc-trace`; no modifica datos crudos.
- `D5-03` no concede permisos `ACT-*` por sí solo y no reemplaza auditoría humana en temas críticos.
  Es el consumidor principal de `svc-runlog`: sobre ese registro evalúa calidad, reintentos y deriva.

### D6 · Legal, Compliance y Riesgos — 4 agentes *(v1: 13 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D6-01` | Legal Corporativo y Contratos | A69, A70, A71 | `svc-privacy`, `svc-validation`, `svc-trace` | Alto |
| `D6-02` | Compliance y Permisos | A72, A73, A74 | `svc-fleet-docs`, `svc-cfdi-validate`, `svc-doc-checklist` | Medio |
| `D6-03` | Riesgos, Seguros y Siniestros | A75, A76, A77 | `svc-alerts`, `svc-trace`, `svc-audit` | Alto |
| `D6-04` | Auditoría Interna | A78, A79, A80, A81 | `svc-audit`, `svc-trace`, `svc-runlog`, `svc-validation` | Medio |

**Límites duros**
- `D6-01` no da opinión legal definitiva, no firma, no aprueba contratos, no sustituye abogado.
- `D6-02` no emite documentos oficiales sin gate ni determina cumplimiento legal final.
- `D6-03` no decide reclamación final ni acepta acuerdos con aseguradora.
- `D6-04` **no busca hallazgos**: `svc-audit` los encuentra por cruce de datos y el agente los
  redacta, prioriza y da seguimiento. No inventa hallazgos ni cierra los críticos sin humano.

### D7 · Talento y Cultura — 3 agentes *(v1: 9 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D7-01` | Reclutamiento y Onboarding | A82, A83, A84 | `svc-privacy`, `svc-validation` | Medio |
| `D7-02` | Nómina y Compensaciones | A85, A86, A87 | `svc-payroll`, `svc-validation`, `svc-privacy` | Medio |
| `D7-03` | Capacitación, Cultura y Desempeño | A88, A89, A90 | `svc-kpi`, `svc-privacy` | Bajo |

**Límites duros**
- `D7-01` **extrae** datos de CVs; **no puntúa candidatos**. La rúbrica es determinística, versionada
  y con atributos protegidos excluidos por lista. No envía expedientes completos al modelo.
- `D7-02` no calcula nómina, no autoriza pagos, no modifica condiciones laborales.
- `D7-03` no sanciona, no despide, no decide aumentos.

### D8 · Calidad, Procesos y Sostenibilidad — 2 agentes *(v1: 9 + líder)*

| ID | Agente | Absorbe | Servicios | Nivel |
|---|---|---|---|---|
| `D8-01` | Procesos, SOPs y Mejora Continua | A91, A92, A93 | `svc-validation`, `svc-audit`, `svc-kpi` | Medio |
| `D8-02` | ESG, Seguridad e Higiene | A94, A95, A96 | `svc-emissions`, `svc-kpi`, `svc-validation` | Bajo |

**Límites duros**
- `D8-01` no modifica procesos sin owner ni aprueba cambios críticos sin el área responsable.
- `D8-02` no certifica cumplimiento ESG, no sustituye al responsable de seguridad, no oculta incidentes.

### O1 · Orquestador General — 1 agente

| ID | Agente | Servicios | Nivel |
|---|---|---|---|
| `O1` | Orquestador General | `svc-runlog`, `svc-rbac`, `svc-budget` | Medio |

`O1` **deja de enrutar por LLM en los casos conocidos**: el ruteo de solicitudes recurrentes es una
tabla de configuración. El modelo interviene sólo ante solicitudes nuevas o ambiguas y ante
integración de entregables multidominio. Abre el `trace_id` de cada caso (§8).

---

## 5-bis. Capa de consultoría — 9 agentes bajo demanda

La v3 eliminó `A50`–`A60` y `A66`–`A68` como plazas de la oficina virtual. Esa decisión sigue
siendo correcta: **no son operación, son proyecto.** Nadie necesita un agente de frontend en
guardia permanente para una transportista.

Pero el ERP sí se está construyendo, y el departamento de Tecnología (`D5`) trabaja en él junto
con Dirección y un equipo externo. Ese equipo externo son **estos agentes, reinstalados como
consultores invocables** — no como estructura.

### 5-bis.1 Qué los hace distintos de los 33

| | Agentes de dominio (`D#-##`, `O1`) | Consultores (`C-##`) |
|---|---|---|
| Quién los activa | Un flujo, el orquestador o un servicio | **Sólo un humano**, explícitamente |
| Cuándo corren | Cuando el proceso lo pide | Cuando se les convoca, nunca solos |
| `ACT-*` | Otorgables uno por uno, con umbral | **Ninguno, jamás.** No tocan el negocio |
| Qué producen | Entregables de operación | Artefactos de proyecto: specs, esquemas, código, revisiones |
| Costo en reposo | Cero (sólo corren en su flujo) | Cero, y además no aparecen en ningún flujo |
| Presupuesto | `svc-budget` operativo por agente | Partida separada de proyecto, por invocación |
| Cuentan en el total | Sí — son 33 | **No.** El motor sigue siendo 33 |

> **Regla dura: un consultor no tiene acceso de escritura a nada de la operación.** No escribe en
> el ERP, no emite documentos, no manda correo, no toca datos de clientes ni de operadores. Lee
> el repo y produce texto y código. Si un consultor necesitara un `ACT-*`, el trabajo no es de
> consultoría: es un agente de dominio y hay que declararlo como tal.

### 5-bis.2 Los nueve

| ID | Consultor | Absorbe | Se convoca para |
|---|---|---|---|
| `C-01` | Producto y UX | A50 | Flujos de pantalla, wireframes, revisión de usabilidad de un módulo |
| `C-02` | Frontend y Design System | A51, A52 | Componentes, formularios, consistencia visual, QA de interfaz |
| `C-03` | Backend y Lógica de Negocio | A53 | Servicios, reglas de negocio, manejo de errores, diseño transaccional |
| `C-04` | Modelo de Datos | A54 | Esquema, relaciones, migraciones, diccionario de datos, performance de consultas |
| `C-05` | Integraciones y APIs | A55 | Endpoints, webhooks, conexión con GPS/TMS/banca/SAT |
| `C-06` | Seguridad Técnica y Accesos | A56, A67 | Roles, permisos, autenticación, revisión de superficie de ataque |
| `C-07` | QA y Testing | A57 | Casos de prueba, regresión, criterios de aceptación, validación de release |
| `C-08` | DevOps, Release y Continuidad | A58, A59, A68 | Despliegue, ambientes, monitoreo, backups, plan de recuperación |
| `C-09` | Documentación Técnica | A60 | Arquitectura escrita, changelog, diagramas, guía de onboarding |

`A66` (IT Admin y soporte interno) **no vuelve**: es `svc-rbac` más herramientas estándar, no un
consultor. `A62` y `A63` tampoco: son Metabase y n8n.

### 5-bis.3 Reglas de invocación

1. **Quién convoca:** Dirección (Gabriel) o `D5-01` Producto y Requerimientos ERP. Nadie más.
2. **Con qué:** un encargo escrito — qué módulo, qué problema, qué restricción. El consultor que
   recibe un encargo ambiguo pide contexto; no lo inventa.
3. **Qué devuelve:** el contrato de entregable de §7.1 aplica igual — supuestos, confianza y
   opciones incluidos. Un consultor que entrega una recomendación única sobre una decisión de
   arquitectura reversible está haciendo mal su trabajo.
4. **Quién decide:** `D5-01` integra y Dirección aprueba. **El consultor recomienda; no elige por
   la empresa.** Una decisión de arquitectura que nadie revisó no es una decisión, es una deuda.
5. **Qué queda registrado:** cada invocación abre `trace_id` en `svc-runlog` igual que un agente
   de dominio, con su encargo, su entregable y su costo. Sin esto no hay forma de saber si la
   consultoría salió más cara que el problema.
6. **Cuándo se apagan:** no se apagan — no están encendidos. No hay fase de roadmap que los
   "encienda"; existen desde que el registro los declara y se usan cuando hacen falta.

### 5-bis.4 Por qué esto no contradice la tesis del documento

La tesis es que la mayor parte del valor temprano es código determinístico, no modelo. Los
consultores **no la violan porque no operan el negocio**: producen el código determinístico. Son
la herramienta con la que se construyen los 31 servicios, no una capa más de agentes razonando
sobre la operación diaria.

El riesgo real de esta capa es distinto: **convocar consultores para evitar decidir.** Nueve
opiniones bien redactadas sobre un esquema de base de datos no sustituyen a alguien que elija uno.
Por eso la regla 4 existe.

---

## 6. Capa determinística — 31 servicios

Estado: `built` (construido) · `planned` (en roadmap). El campo vive en
`registry/services/*.yaml` y hace verificable el roadmap por máquina (§10.3).

### 6.1 Capa de datos — prerrequisito de todo

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-masterdata` | *(hueco v1)* | Catálogo único: clientes, unidades, operadores, rutas, tarifas | 0 |
| `svc-ingest` | *(hueco v1)* | Normalización de bancos, tickets de diesel, GPS, CSV del ERP | 0 |

### 6.2 Finanzas

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-costing` | A10 | Costo por km y por viaje: diesel, casetas, operador, mantenimiento, llantas, seguro, depreciación, fijos asignados | 0 |
| `svc-profitability` | A11 | Margen por viaje, ruta, cliente, unidad, operador | 0 |
| `svc-scenarios` | A12 | Sensibilidad, punto de equilibrio, escenarios min/objetivo/óptimo | 4 |
| `svc-financials` | A7, A8 | EEFF, EBITDA, ROIC, liquidez, variaciones vs. presupuesto | 4 |
| `svc-treasury` | A14 | Posición de caja, flujo diario y semanal, días de caja | 3 |
| `svc-ar` | A15 | Aging de cartera, riesgo de morosidad, flujo esperado | 2 |
| `svc-ap` | A16 | Calendario de pagos, vencimientos, priorización | 3 |
| `svc-invoicing` | *(hueco v1)* | Emisión y timbrado; incluye demoras y estadías como concepto facturable | 2 |
| `svc-cfdi-validate` | A18, A74 | Validación XSD + reglas SAT de CFDI y Carta Porte. Un LLM aquí sólo añade riesgo | 2 |

### 6.3 Operaciones

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-routing` | A21 | Distancia, ETA, casetas — vía API de ruteo | 5 |
| `svc-capacity` | A22 | Asignación unidad-operador-viaje como problema de restricciones | 5 |
| `svc-telemetry` | A24, A34 | Geocercas, desvíos, paradas no autorizadas, retrasos. Corre 24/7 | 5 |
| `svc-fleet-docs` | A27, A73 | Vigencias de pólizas, permisos, verificaciones — aritmética de fechas | 5 |
| `svc-maintenance` | A28 | Disparadores de servicio por kilometraje y horas | 5 |
| `svc-fuel` | A29 | km/litro, consumo esperado vs. real, detección estadística de anomalías | 5 |
| `svc-doc-checklist` | A32 | Completitud documental del viaje antes de facturar | 2 |
| `svc-emissions` | A95 | Emisiones = factor × litros | 7 |

### 6.4 Comercial

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-pricing` | A38 | Tarifa = `svc-costing` + margen objetivo + política de descuento | 1 |

### 6.5 Talento

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-payroll` | A85, A86, A87 | Pre-nómina, bonos, validación de incidencias | 7 |

### 6.6 Transversales

| Servicio | Reemplaza | Función | Fase |
|---|---|---|---|
| `svc-kpi` | A4 | Indicadores globales y por departamento | 3 |
| `svc-alerts` | A5 | Motor de reglas sobre umbrales: liquidez, margen, vencimientos, desvíos. **Selecciona qué entra a los briefs** (§9.2) | 3 |
| `svc-notify` | A26 (parcial) | Plantillas fijas de aviso a cliente y operador, sin LLM | 2 |
| `svc-validation` | A9, A13, A40, A57, A87, A92 | QA transversal: reglas determinísticas por dominio | 1 |
| `svc-trace` | A98 | Reconciliación **cifra ↔ consulta origen**. Bloquea entregables que no cuadran | 1 |
| `svc-runlog` | *(hueco v1 y v2)* | **Registro del camino y el progreso de cada caso** (§8) | 1 |
| `svc-audit` | A78, A79, A80 | Auditoría continua por cruce de datos | 6 |
| `svc-rbac` | A56, A67 | Matriz de roles y permisos | 6 |
| `svc-privacy` | *(hueco v1)* | Clasificación y redacción de PII, retención | 6 |
| `svc-budget` | *(hueco v1)* | Presupuesto de tokens por agente, alerta al 80% | 1 |

**Infraestructura estándar** — no son servicios de negocio, son herramientas de mercado:
CI/CD → GitHub Actions · Monitoreo → Sentry/Grafana · Dashboards → Metabase ·
Workflows → n8n o Temporal · Backups → cron. Sustituyen a A58, A59, A62, A63, A68.

---

## 7. Comunicación agente ↔ persona (objetivo O3)

La v1 y la v2 daban por hecha esta capa. Es la que determina si la oficina virtual se siente útil
o se siente como un generador de documentos que alguien tiene que auditar a mano.

### 7.1 Contrato de entregable — sobre obligatorio

**Toda salida dirigida a una persona lleva estos seis campos.** `svc-validation` rechaza el
entregable si falta alguno.

| Campo | Contenido |
|---|---|
| `decision_solicitada` | Qué se te pide decidir — o explícitamente "ninguna, es informativo" |
| `fuentes` | De dónde salió cada cifra (`svc-trace` ya tiene el dato; aquí sólo se expone) |
| `supuestos` | Qué se asumió para llegar al resultado |
| `confianza` | Nivel de certeza y qué lo limita (hereda `CTL-CONF` de la v2) |
| `opciones` | Cuando hay más de un camino razonable, se presentan las opciones — **no una recomendación única disfrazada de conclusión** |
| `si_no_respondes` | Qué ocurre con el caso si nadie actúa, y en cuánto tiempo |

### 7.2 Bandeja única de HITL

Todas las solicitudes de aprobación llegan a **una sola bandeja**, no a WhatsApp según el agente y
a correo según el otro. Si el canal se fragmenta, el Gate de Autoridad existe en el papel y no en
la operación.

Cada solicitud lleva: `trace_id`, agente solicitante, acción `ACT-*` pedida, umbral que la disparó,
resumen de una línea, entregable completo enlazado, y **SLA**.

### 7.3 Regla dura de timeout

> **Un HITL vencido escala o expira. Nunca auto-aprueba.**

| Criticidad | SLA | Al vencer |
|---|---|---|
| Alta (pago, CFDI, contrato, siniestro severo) | 4 h hábiles | Escala al siguiente nivel; el caso queda `bloqueado` |
| Media | 1 día hábil | Escala una vez; luego expira |
| Baja | 3 días hábiles | Expira y se cierra como `no_atendido` |

Toda expiración y todo escalamiento quedan en `svc-runlog`. Un caso que expira repetidamente es
señal de un umbral mal calibrado, y aparece en la evaluación de `D5-03`.

### 7.4 Tono y honestidad del agente

- El agente **declara la incertidumbre**, no la esconde tras redacción segura.
- Si un servicio falló o un dato faltaba, el entregable lo dice; no se completa el hueco con prosa.
- Nada de recomendación única cuando el caso admite varias lecturas razonables.

---

## 8. Trazabilidad del camino y el progreso (objetivo O4)

Este era el hueco más grande de la v2. `svc-trace` responde *"¿de dónde salió este número?"*.
No responde *"¿por dónde pasó este caso y en qué va?"*.

> **`svc-trace` = trazabilidad de cifras. `svc-runlog` = trazabilidad de proceso.**
> Se mantienen separados a propósito: distinta pregunta, distinto consumidor, distinta retención.

### 8.1 `svc-runlog` — registro del camino

`O1` abre un `trace_id` por solicitud y **todo paso posterior lo hereda**. Cada paso registra:

| Campo | Contenido |
|---|---|
| `trace_id` / `span_id` / `parent_span_id` | Árbol completo del caso |
| `actor` | Agente o servicio que ejecutó el paso |
| `tipo` | `ruteo` · `llamada_llm` · `llamada_servicio` · `validacion` · `gate` · `accion` · `entrega` |
| `decision_ruteo` | Tabla o LLM, y por qué |
| `entradas` / `salidas` | Referencias; los payloads con PII se guardan redactados por `svc-privacy` |
| `prompt_version` / `rubrica_version` / `servicio_version` | Qué versión produjo el resultado |
| `resultado` | `ok` · `fallo` · `reintento` · `bloqueado` |
| `tokens` / `costo` / `latencia` | Alimenta `svc-budget` |
| `gate` | Umbral disparado, quién aprobó o rechazó, y cuándo |

El registro es **inmutable y append-only**. Su consumidor principal es `D5-03` (AgentOps) y su
consumidor de control es `D6-04` (Auditoría).

**Los reintentos se registran siempre.** El flujo de corrección (§12.3) permite dos reintentos; sin
registro, un agente que falla sistemáticamente al primer intento y acierta al segundo se ve
perfecto desde fuera mientras se degrada por dentro.

### 8.2 Estado del caso — progreso consultable

El progreso no es narrativa: es una máquina de estados con timestamp por transición.

```
recibido → en_proceso → esperando_validacion → esperando_humano → entregado
                │              │                      │
                │              └── rechazado_validacion (máx. 2 reintentos)
                │                                     │
                └────────── bloqueado ◄───────────────┴── expirado
```

Cualquiera puede preguntar "¿en qué va la cotización de X?" y obtener estado, responsable actual,
tiempo en ese estado y siguiente paso — sin invocar un LLM.

### 8.3 Versionado de definiciones

`registry/` vive en git. Cada cambio de prompt, rúbrica, umbral o contrato de servicio queda con
autor y fecha. `svc-runlog` guarda la versión usada en cada ejecución, de modo que un entregable
de hace tres meses es reproducible contra la definición vigente entonces.

### 8.4 Privacidad y retención

`svc-privacy` clasifica PII, redacta antes de enviar al modelo, prohíbe enviar expedientes
completos al LLM y define retención. Aplica también a `svc-runlog`: el registro guarda referencias
y payloads redactados, no expedientes íntegros. En México esto cae bajo LFPDPPP.

---

## 9. Reducción de sesgos (objetivo O2)

### 9.1 Regla general de rúbricas

> **Todo ranking, score o priorización con consecuencia sale de una rúbrica versionada y
> determinística. El LLM extrae y explica; no ordena.**

La v2 aplicaba esto sólo a personas. En v3 aplica a todo caso con consecuencia:

| Ranking | Quién lo produce | Registro |
|---|---|---|
| Candidatos a un puesto | Rúbrica versionada, atributos protegidos excluidos por lista | `rubrica_version` + decisión humana registrada |
| Operadores (desempeño, asignación) | `svc-capacity` (restricciones) + rúbrica | `rubrica_version` |
| Prospectos y clientes | Rúbrica comercial versionada | `rubrica_version` |
| Proveedores | Criterios explícitos y ponderados, no juicio del modelo | `rubrica_version` |
| Prioridad de cobranza | `svc-ar` por aging y riesgo | determinístico |
| Prioridad de pagos | `svc-ap` por vencimiento y política | determinístico |
| Severidad de incidencias | Tabla de severidad (§11 umbrales) | determinístico |

Toda salida que incluya un orden lleva `rubrica_version` en el sobre del entregable (§7.1).

### 9.2 Sesgo de selección en briefs

`D1-03` produce el daily brief y, con ello, moldea lo que la dirección ve todos los días. Si el
modelo elige el contenido, el sesgo entra sin que nadie lo note.

> **`svc-alerts` selecciona qué entra al brief según reglas y umbrales. `D1-03` narra lo
> seleccionado y no puede omitir ni añadir temas.**

Lo mismo aplica a los reportes de `D5-02` y `D6-04`: los hallazgos los produce el servicio; el
agente los redacta y prioriza dentro de lo que el servicio entregó.

### 9.3 Muestreo humano

`svc-validation` cubre reglas, no criterio. `D5-03` toma una muestra periódica de entregables por
agente y la somete a revisión humana; el resultado alimenta la evaluación del agente. Un LLM
revisando a otro LLM no es garantía — ese fue el error E3 de la v1.

---

## 10. Registro — la fuente de verdad ejecutable

### 10.1 Agente

```yaml
id: D4-03
name: Pricing y Propuestas
department: 04-comercial-cliente
teams:
  - pricing-cotizaciones-propuestas
mission: Generar propuestas comerciales rentables usando pricing determinístico.
estado: planned          # planned | built | deprecated
fase: 1
model_tier: medium
absorbe: [A38, A39, A40]
tools:
  - svc-pricing
  - svc-costing
  - svc-profitability
  - svc-validation
  - svc-trace
  - svc-runlog
inputs: [solicitud_cliente, ruta, volumen, tipo_servicio, margen_objetivo]
outputs: [cotizacion, propuesta_comercial, email_sugerido]
actions:
  - ACT-EMAIL-S
controls:
  - CTL-HITL
  - CTL-LIMIT
  - CTL-AUDIT
limits:
  - no_calcula_precio
  - no_envia_sin_autorizacion
  - no_aprueba_margen_bajo
prompt_version: v1.0.0
```

### 10.2 Servicio

```yaml
id: svc-costing
name: Servicio de Costeo Logístico
type: deterministic_python
estado: planned
fase: 0
owner_domain: [02-finanzas, 03-operaciones]
consumidores: [D2-03, D4-03]
inputs:
  - route_id
  - unit_id
  - fuel_price
  - driver_cost
  - tolls
  - maintenance_factor
  - tire_factor
  - insurance_factor
  - fixed_cost_allocation
outputs:
  - cost_per_km
  - total_trip_cost
  - variable_cost
  - fixed_allocated_cost
  - assumptions
tests:
  - test_cost_per_km
  - test_missing_fuel_price
  - test_negative_distance_blocked
controls: [svc-validation, svc-trace]
version: v1.0.0
```

### 10.3 `validate_registry.py` — validaciones obligatorias

Los 7 errores de consistencia de la v1 se habrían detectado solos. Las reglas:

| # | Regla |
|---|---|
| 1 | Toda habilidad referenciada existe en el catálogo |
| 2 | Todo servicio declarado por un agente existe en `registry/services/` |
| 3 | **Todo `ACT-*` tiene al menos un `CTL-*` asociado** |
| 3b | **Ningún `C-##` declara un `ACT-*`** (§5-bis) |
| 4 | Ninguna capacidad del catálogo queda huérfana (definida y sin usar) |
| 5 | **Todo equipo tiene owner humano y owner digital** (agente `D#-##`, servicio `svc-*`, consultor `C-##` o la cadena `humano`) |
| 6 | **Todo equipo tiene agente asociado o razón explícita de cobertura** (§4.1) |
| 7 | **Todo servicio declara al menos un test y al menos un consumidor** |
| 8 | **Ningún agente `built` depende de un servicio `planned`** |
| 9 | Todo agente pertenece a un departamento y a al menos un equipo existentes |
| 10 | Todo agente declara `model_tier` y todo servicio declara `fase` |

---

## 11. Gate de Autoridad

### 11.1 Qué controla

Pagos · descuentos · cotizaciones · emisión de CFDI · envío de correo externo · contratos ·
contrataciones · bajas de personal · cambios de ruta críticos · incidencias severas · escritura en
ERP · uso de datos personales.

### 11.2 Tipos de control

| Código | Significado |
|---|---|
| `CTL-ESC` | Escala: notifica a un humano y **el flujo continúa** |
| `CTL-HITL` | Bloquea: **se detiene** hasta aprobación humana registrada |
| `CTL-LIMIT` | Umbral numérico duro (§11.4) |
| `CTL-AUDIT` | Bitácora inmutable obligatoria |
| `CTL-POLICY` | Cumplimiento de política interna |
| `CTL-PRIVACY` | Privacidad / PII |
| `CTL-CONF` | Certeza y supuestos explícitos (§7.1) |
| `CTL-REJECT` | Devolución por error |
| `CTL-VERSION` | Versionado |

### 11.3 Acciones controladas

| Código | Acción | Control mínimo |
|---|---|---|
| `ACT-ERP-W` | Escritura en el ERP | Whitelist de entidades + bitácora |
| `ACT-EMAIL-S` | Envío real de correo/mensaje | `CTL-HITL` si es externo y no es plantilla de `svc-notify` |
| `ACT-DOC-S` | Emisión de documento oficial (CFDI, Carta Porte) | `CTL-HITL` siempre |
| `ACT-PAY` | Instrucción de pago | `CTL-HITL` siempre + doble factor |
| `ACT-NOTIFY` | Notificación interna | Libre |

> **Regla dura: ningún agente tiene `ACT-*` por defecto.** Se otorga agente por agente, con umbral,
> y `D5-03` no puede concederlo por sí solo.

### 11.4 Tabla de umbrales — hace implementable `CTL-LIMIT`

Valores por defecto. **Deben calibrarse con cifras reales antes de encender nada.** Viven en
`registry/policies/authority-gate.yaml` y en `docs/umbrales.md`.

| Decisión | Agente decide solo | Humano operativo | Dirección |
|---|---|---|---|
| Pago a proveedor | ≤ $5,000 MXN con OC previa y proveedor registrado | $5,000 – $100,000 | > $100,000 |
| Descuento sobre tarifa | ≤ 3% | 3% – 8% | > 8% |
| Cotización | Margen ≥ objetivo y desviación ≤ 5% | Margen entre mínimo y objetivo | Margen < mínimo |
| Cobranza | Recordatorio con plantilla, ≤ 15 días vencido | 15 – 60 días | > 60 días o vía legal |
| Compromiso de viaje | Unidad y operador disponibles, documentos vigentes | Cualquier restricción incumplida | — |
| Incidencia en ruta | Severidad 1–2: registra y notifica | Severidad 3 | Severidad 4–5 (robo, accidente) |
| Emisión de CFDI | Nunca | Siempre revisa | — |
| Contratación / baja | Nunca | Prepara expediente | Autoriza |
| Contrato con cliente | Nunca | Redacta y marca riesgos | Firma |

Toda `ACT-PAY` y `ACT-DOC-S` es `HITL`. Toda `ACT-EMAIL-S` externa es `HITL` salvo plantilla fija
de `svc-notify` con variables validadas (ej. "su unidad salió a las HH:MM"), que no pasa por LLM.

### 11.5 Gobierno de costo

| Nivel | Uso | Agentes |
|---|---|---|
| **Alto** | Juicio complejo, baja frecuencia | `D1-01`, `D5-03`, `D6-01`, `D6-03` |
| **Medio** | Operación diaria con criterio | `O1` y la mayoría de D2, D3, D4, D5, D6, D7, D8 |
| **Bajo** | Clasificación, resumen, plantillas, alta frecuencia | `D1-03`, `D3-02`, `D4-02`, `D4-04`, `D4-05`, `D7-03`, `D8-02` |
| **Código** | Costo cero | los 31 servicios |

`svc-budget` impone tope mensual por agente y alerta al 80%. `svc-runlog` provee el consumo real.

---

## 12. Flujos operativos

### 12.1 Flujo normal

```
Solicitud
   │  ── O1 abre trace_id ──►  svc-runlog
   │
   ├─ ¿recurrente y conocida? ──► ruteo por tabla (sin LLM)
   │                                       │
   └─ ¿nueva o ambigua? ──► Orquestador ───┘
                                           │
                                 Agente de dominio
                                           │
                              servicios determinísticos
                                           │
                                svc-validation + svc-trace
                                           │
                                    ¿criticidad baja?
                                           │
                            Entrega + contrato §7.1 + bitácora
```

### 12.2 Flujo crítico

**Criticidad alta** = ejecuta un `ACT-*` con efecto externo, supera un umbral de §11.4, o produce
un documento fiscal o legal. Todo lo demás es criticidad baja y se entrega sin gate.

```
… svc-validation + svc-trace
        │
   Gate de Autoridad (§11.4)
        │
   Bandeja HITL con SLA (§7.2)
        │
   Humano aprueba / rechaza / vence (§7.3)
        │
   Acción controlada  ──►  bitácora + svc-runlog
```

### 12.3 Flujo de corrección

```
Agente produce
     │
svc-validation / svc-trace
     │
   ¿falla? ──► devuelve al agente ──► corrige ──► reintenta
                                                     │
                            máximo 2 reintentos, cada uno en svc-runlog
                                                     │
                                      si persiste ──► escala a humano
                                                      estado: bloqueado
```

Esto baja el promedio de **4–6 llamadas LLM por entregable (v1) a 1–2**.

---

## 13. Reglas de diseño de agentes

**R1 — Un agente por proceso de negocio.** No por microtarea.
Mal: `Agente ROE` + `Agente ROA` + `Agente EBITDA`. Bien: `D2-01` + `svc-financials`.

**R2 — Un número, una fuente.**
`costo/km → svc-costing` · `precio → svc-pricing` · `margen → svc-profitability` ·
`CFDI → svc-cfdi-validate` · `nómina → svc-payroll` · `KPI → svc-kpi`

**R3 — El agente explica, no calcula.** Puede decir *"el margen cayó porque el diesel subió y la
ruta tuvo más tiempo muerto"*. El número viene del servicio.

**R4 — Ninguna acción externa sin control.** Cliente, dinero, documento oficial, ERP o personas ⇒ Gate.

**R5 — Equipos como organización, agentes como ejecución.** Los equipos no cuestan tokens.

**R6 — Líderes como gobierno, no como llamada obligatoria.**

**R7 — Todo paso deja rastro.** Si no está en `svc-runlog`, no ocurrió.

**R8 — Todo orden con consecuencia sale de rúbrica versionada** (§9.1).

**R9 — Todo entregable a una persona lleva el contrato del §7.1.**

---

## 14. Estructura del repositorio

```
AI-company/
├── docs/
│   ├── arquitectura-v3.md          ← este documento (vigente)
│   ├── arquitectura-v2.md          ← histórico
│   ├── arquitectura-v1.md          ← histórico (cargado y verificado)
│   ├── owners-equipos.csv          ← §4.3, los 42 equipos con owner y carga compartida
│   ├── catalogo-habilidades.md
│   ├── catalogo-agentes.md
│   ├── catalogo-servicios.md
│   ├── umbrales.md                 ← §11.4, calibrable
│   ├── politicas-act.md
│   ├── contrato-entregable.md      ← §7.1
│   ├── trazabilidad.md             ← §8
│   ├── rubricas.md                 ← §9.1, versionadas
│   ├── privacidad-datos.md
│   └── roadmap-implementacion.md
├── registry/
│   ├── agents/                     ← 33 definiciones YAML
│   ├── consultants/                ← 9 consultores bajo demanda (§5-bis)
│   ├── services/                   ← 31 contratos
│   ├── teams/                      ← 42 equipos con owner
│   └── policies/
│       ├── authority-gate.yaml
│       ├── rbac.yaml
│       ├── privacy.yaml
│       └── budget.yaml
├── services/                       ← Python determinístico
├── agents/                         ← prompts, herramientas, orquestador, runtime
├── erp/                            ← schema, migrations, api
├── tests/                          ← unit, integration, validation, agent_evals
└── scripts/
    ├── validate_registry.py        ← §10.3
    ├── check_permissions.py
    ├── run_agent_eval.py
    └── sync_masterdata.py
```

---

## 15. Roadmap

El error más caro sería construir 33 agentes antes de que uno solo demuestre retorno.

### Fase 0 — Fundación de datos *(semanas 1–3, cero IA)*
`svc-masterdata` · `svc-ingest` · `svc-costing` · `svc-profitability`

Sin un solo agente ya obtienes **costo por km y margen real por viaje, ruta, cliente y unidad**.
Para una transportista en arranque suele ser el mayor retorno individual del proyecto: 100% código,
testeable, sin riesgo de alucinación.

### Fase 1 — Cotizar sin perder margen *(semanas 4–7)*
`svc-pricing` · `svc-validation` · `svc-trace` · `svc-runlog` · `svc-budget` ·
**`D4-03` Pricing y Propuestas** · **`D2-03` Costos y Márgenes**

Primeros 2 agentes. Precio calculado en Python, propuesta redactada por IA, gate de margen mínimo
determinístico. `svc-runlog` entra aquí, con el primer agente: la trazabilidad no se retrofitea.

### Fase 2 — Cerrar el ciclo operación → ingreso *(semanas 8–11)*
`svc-doc-checklist` · `svc-invoicing` · `svc-cfdi-validate` · `svc-ar` · `svc-notify` ·
**`D3-05` Evidencias y Cierre** · **`D2-04` Ciclo de Ingreso**

Cierra el hueco de facturación de la v1 y acelera el ciclo de cobro.

### Fase 3 — Visibilidad ejecutiva *(semanas 12–16)*
`svc-treasury` · `svc-ap` · `svc-kpi` · `svc-alerts` · **`D1-03` Síntesis Ejecutiva**

Daily brief y alertas de liquidez con datos verificados. La selección de contenido la hace
`svc-alerts`, no el agente (§9.2).

> ### ⬛ Corte de MVP — **5 agentes IA + 18 servicios**
>
> Agentes: `D4-03`, `D2-03`, `D3-05`, `D2-04`, `D1-03`.
> Servicios: los de las fases 0 a 3.
>
> **Aquí se para y se evalúa.** Nada de las fases 4–7 se enciende sin que el MVP demuestre
> retorno medible: margen protegido en cotizaciones, días de cobro reducidos, brief diario
> confiable. Si el MVP no lo demuestra, el problema no se arregla añadiendo agentes.
>
> Nota: la relación agentes/servicios se invierte respecto a lo que sugiere el titular de la
> arquitectura. **La mayor parte del valor temprano es código, no modelo** — y eso es la tesis
> de todo el diseño, no una concesión.

### Fase 4 — Control financiero completo *(mes 5+)*
`svc-financials` · `svc-scenarios` ·
**`D2-01` Controller** · **`D2-02` FP&A** · **`D2-05` Ciclo de Egreso** · **`D2-06` Fiscal y Documental** ·
**`O1` Orquestador**

`O1` entra aquí y no antes: con 5 agentes el ruteo es una tabla y un orquestador LLM sería costo
sin función. Se enciende cuando aparece el primer caso multidominio real.

### Fase 5 — Operación en tiempo real
`svc-routing` · `svc-capacity` · `svc-telemetry` · `svc-fleet-docs` · `svc-maintenance` · `svc-fuel` ·
**`D3-01`, `D3-02`, `D3-03`, `D3-04`, `D3-06`**

### Fase 6 — Legal, compliance y riesgos
`svc-audit` · `svc-rbac` · `svc-privacy` · **`D6-01`, `D6-02`, `D6-03`, `D6-04`**

`svc-privacy` se adelanta a la fase 0 **si antes de esta fase algún agente procesa PII** — CVs,
expedientes o GPS de operadores. La fase indica cuándo se construye completo, no un permiso para
operar sin él.

### Fase 7 — Dirección, talento, calidad, ESG, comercial ampliado y AgentOps *(sólo bajo demanda real)*
`svc-payroll` · `svc-emissions` ·
**`D1-01`, `D1-02`, `D4-01`, `D4-02`, `D4-04`, `D4-05`, `D5-01`, `D5-02`, `D5-03`,
`D7-01`, `D7-02`, `D7-03`, `D8-01`, `D8-02`**

Ninguno se enciende sin un caso de uso que lo pida. `D5-03` (AgentOps) se adelanta en cuanto haya
más de ~8 agentes activos: a partir de ahí la calidad del conjunto deja de poder vigilarse a mano.

### Resumen de acumulados

| Al cerrar | Agentes | Servicios |
|---|---|---|
| Fase 0 | 0 | 4 |
| Fase 1 | 2 | 9 |
| Fase 2 | 4 | 14 |
| **Fase 3 — MVP** | **5** | **18** |
| Fase 4 | 10 (incluye `O1`) | 20 |
| Fase 5 | 15 | 26 |
| Fase 6 | 19 | 29 |
| Fase 7 | **33** | **31** |

---

## 16. Lo que cambia en la práctica

| Antes | Con la v3 |
|---|---|
| El costo por km depende de qué agente lo calcule | Un solo servicio, un solo número, con test |
| Un error de cálculo del LLM llega a una cotización | Imposible: el LLM no calcula |
| 108 agentes por mantener y presupuestar | 33 agentes + 31 funciones Python |
| Todo entregable pasa por 4 revisiones | Sólo lo crítico |
| Un agente podía escribir a un cliente sin filtro | Comunicación externa con HITL o plantilla fija |
| Sin política de datos personales | `svc-privacy` con redacción y retención |
| "¿Por qué este agente concluyó esto?" no tenía respuesta | `svc-runlog`: camino completo con `trace_id` |
| "¿En qué va mi solicitud?" había que preguntarlo | Estado consultable, sin invocar LLM |
| El entregable llegaba sin fuentes ni supuestos | Contrato obligatorio de §7.1 |
| Un ranking podía salir del criterio del modelo | Rúbrica versionada registrada en cada salida |
| Un HITL sin respuesta quedaba en el limbo | SLA con escalamiento; nunca auto-aprueba |
| La v2 borraba la empresa para salvar el motor | Organización y ejecución coexisten, separadas |

---

## 17. Estado de cierre de la v3

**`v3.0.1` — los cinco pendientes están cerrados.** Tres por decisión, uno con datos reales del
organigrama y uno cargando el documento faltante.

### 17.1 Cómo quedó cada uno

| # | Pendiente | Resolución |
|---|---|---|
| 1 | Calibrar umbrales §11.4 | **Parcialmente calibrado con cifras reales.** 6 de 10 umbrales salen del organigrama firmado (junio 2026) y ya no son propuestas. Los 4 restantes dependen de costo por km — Fase 0. Cada umbral declara su propio `calibrado:` |
| 2 | Owners de los 42 equipos | **Poblados** desde el organigrama de Fleeter, con modelo de propiedad compartida (§4.3). 42 archivos en `registry/teams/` |
| 3 | Rúbricas de §9.1 | **Reclasificadas a pre-Fase 7.** Ninguna alimenta a los 5 agentes del MVP; la regla dura (ningún ranking con consecuencia sale del LLM) rige desde hoy |
| 4 | Canal de la bandeja HITL §7.2 | **Panel del ERP**, con WhatsApp como aviso que enlaza. Es requisito de entrada de la Fase 1 y entra al alcance del ERP que D5 construye con la capa de consultoría (§5-bis). SLA de §7.3 sin cambio. Ruteo: al `owner_humano` del equipo |
| 5 | Cargar `arquitectura-v1.md` | **Cargado.** 99 agentes `A1`–`A99`, completos y sin huecos. La verificación encontró tres defectos — §17.3 |

### 17.2 Umbrales que ya son reales

Vienen del organigrama, no de la arquitectura:

| Umbral | Cifra real | Autoridad |
|---|---|---|
| Pago a proveedor | > $20,000 MXN | Gabriel (Nay ejecuta por debajo) |
| Descuento sobre tarifa | > 5% | Gabriel (Ana negocia por debajo) |
| Plazo de pago | > 45 días | Gabriel |
| Contrato con cliente | Firma siempre; > $100K/año por definición | Gabriel |
| Emisión de CFDI + Carta Porte | SLA de 24 h post-entrega | Nay emite, Gabriel valida excepciones |
| Fondo de emergencia | 3 meses de costos fijos, intocable sin HITL de Dirección | Gabriel |

Quedan sin calibrar: **cotización** (margen objetivo y mínimo por ruta), **cobranza** (días de
vencimiento), **incidencia en ruta** (tabla de severidad 1–5). Los tres son requisito de salida
de la Fase 0 o de acuerdo explícito con Ana y Elias.

**Hallazgo que cambia el diseño de `svc-pricing`:** el gate determinístico de cotización **ya
existe en la operación** — es la tabla de precios pre-aprobada que Gabriel fija por ruta y
actualiza mensualmente. `svc-pricing` la **consume como dato maestro**; no la reinventa. Lo que
falta no es el mecanismo, es sistematizar los márgenes mínimos que hoy viven en esa tabla.

### 17.3 Defectos que encontró la verificación contra la v1

Para esto servía cargar la v1:

| Hallazgo | Estado |
|---|---|
| **`A14` Tesorería y Liquidez quedó huérfano.** §4.1 asignaba el equipo a `D2-01`, pero la columna "Absorbe" no lo listaba: un agente de la v1 desaparecido sin justificación | **Corregido** — `D2-01` absorbe A7, A8, A9, A14 |
| **`A62` Dashboards y `A63` Automatización** no aparecían ni como absorbidos ni como eliminados | **Corregido** — declarados como cobertura sin agente (Metabase y n8n/Temporal) |
| `A50`–`A60` y `A66`–`A68` | Correctos: eliminados con justificación explícita en §5 |

Cobertura final: los 99 agentes de la v1 están absorbidos o eliminados con razón escrita.

### 17.4 Inconsistencia de la regla #5, resuelta

La validación #5 de §10.3 exige owner humano y digital en todo equipo, pero §4.1 declara tres
equipos sin agente por diseño. **El owner digital puede ser un agente `D#-##`, un servicio `svc-*`
o la cadena `humano`.** La #5 verifica que el campo esté poblado y sea uno de esos tres tipos; la
#6 sigue exigiendo la razón explícita de cobertura, que es lo que evita el equipo fantasma.

### 17.5 Condiciones de arranque

| Antes de | Debe existir |
|---|---|
| **Fase 0** | Nada pendiente. No enciende agentes ni ejecuta `ACT-*` — **puede arrancar ya** |
| **Fase 1** (primer agente) | Margen objetivo y mínimo por ruta calibrados · **bandeja de HITL del ERP en producción** con los SLA de §7.3 · `validate_registry.py` en verde |
| **Fase 5** (operación en tiempo real) | Tabla de severidad de incidencias 1–5 acordada con Elias y Ana |
| **Fase 7** (primer agente de ranking) | Rúbricas de §9.1 versionadas, con criterios, pesos y atributos excluidos |
