<!--
Documento histórico. Cargado el 2026-08-17 desde "IA estructura.md".
Es la v1 de la arquitectura: 108 agentes (1 orquestador + 8 líderes + 99 núcleo), 31 equipos.
Se conserva sin editar. La auditoría de sus errores está en docs/arquitectura-v2.md;
la arquitectura vigente es docs/arquitectura-v3.md.
Sirve para verificar la columna "Absorbe A##" de la v3 contra su origen (§17 v3, pendiente 5).
-->

# **Reporte Final Integrado de la Oficina Virtual de Agentes IA**

## **1\. Visión general**

La Oficina Virtual de Agentes IA será la empresa digital paralela de la compañía. Su objetivo es operar con la estructura, disciplina y capacidad analítica de una empresa global, pero con una base altamente eficiente de agentes especializados y multirol.

La oficina virtual no sustituye al equipo humano. Lo complementa, reduce carga operativa, acelera análisis, mejora documentación, detecta errores, genera reportes, prepara decisiones y permite que el equipo humano se concentre en estrategia, relaciones, supervisión y ejecución crítica.

La lógica central será:

Los agentes producen, analizan, documentan y revisan.  
Los humanos supervisan, deciden, autorizan y asumen responsabilidad final.  
---

## **2\. Arquitectura general**

La estructura final recomendada es:

Dirección Humana  
│  
└── Agente Orquestador General  
    │  
    ├── 8 Agentes Líderes de Departamento  
    │  
    ├── 31 Equipos Digitales  
    │  
    └── 99 Agentes Núcleo Operativos

## **3\. Composición total**

| Nivel | Cantidad |
| ----- | ----- |
| Agente Orquestador General | 1 |
| Agentes Líderes de Departamento | 8 |
| Equipos Digitales | 31 |
| Agentes Núcleo Operativos | 99 |
| **Total de agentes** | **108** |

---

# **4\. Departamentos de la oficina virtual**

La oficina se divide en 8 departamentos:

1. **Dirección y Gobierno**  
2. **Finanzas, Contabilidad y Administración**  
3. **Operaciones Logísticas**  
4. **Comercial y Cliente**  
5. **Tecnología, Datos e Innovación**  
6. **Legal, Compliance y Riesgos**  
7. **Talento y Cultura**  
8. **Calidad, Procesos y Sostenibilidad**

Cada departamento tiene:

* Un agente líder de departamento.  
* Equipos especializados.  
* Agentes núcleo.  
* Procesos asignados.  
* Entradas.  
* Salidas.  
* Criterios de calidad.  
* Límites de decisión.  
* Escalamiento humano.

---

# **5\. Catálogo maestro de habilidades**

Para evitar crear agentes innecesarios, cada agente tendrá una combinación de habilidades. No todos los agentes necesitan todas las capacidades. Cada agente debe tener solo las habilidades necesarias para cumplir su misión.

## **5.1 Habilidades de lectura e input**

| Código | Habilidad | Qué hace | Valor para la oficina |
| :---- | :---- | :---- | :---- |
| IN-TXT | Lectura de texto | Interpreta instrucciones, notas, políticas, minutas y reportes | Convierte texto en acciones |
| IN-PDF | Lectura de PDF | Extrae información de contratos, facturas, reportes, manuales o documentos formales | Permite trabajar con documentos empresariales reales |
| IN-XLSX | Lectura de Excel/XLSX | Analiza tablas, fórmulas, presupuestos, rutas, estados financieros y costos | Clave para finanzas, operaciones y control |
| IN-CSV | Lectura de CSV | Procesa datos exportados de ERP, GPS, bancos o sistemas externos | Facilita análisis masivo de datos |
| IN-IMG | Lectura de imágenes | Interpreta fotos, comprobantes, evidencias de entrega, daños o documentos escaneados | Útil para operación, siniestros y evidencias |
| IN-EMAIL | Lectura de correos | Interpreta solicitudes, acuerdos, seguimientos o respuestas | Útil para clientes, proveedores, cobranza y ventas |
| IN-ERP | Lectura de ERP | Consulta entidades internas como clientes, viajes, facturas, unidades y operadores | Permite automatización real |
| IN-DB | Lectura de base de datos | Consulta datos estructurados y relaciones | Soporte para BI, dashboards y análisis técnico |
| IN-DASH | Lectura de dashboards | Interpreta KPIs, gráficas y semáforos | Facilita decisiones ejecutivas |
| IN-DOCS | Lectura documental | Revisa expedientes, contratos, permisos, actas, pólizas y archivos internos | Reduce errores documentales |
| IN-GPS | Lectura GPS/telemetría | Interpreta ubicación, ETA, desvíos, paradas y rutas | Clave para torre de control |
| IN-API | Lectura de APIs | Recibe o consulta datos de sistemas externos | Permite integraciones |

---

## **5.2 Habilidades de procesamiento**

| Código | Habilidad | Qué hace | Valor |
| :---- | :---- | :---- | :---- |
| PR-CLASS | Clasificación | Ordena información por tipo, área, prioridad o riesgo | Evita caos operativo |
| PR-EXT | Extracción de datos | Extrae datos clave de documentos, tablas o mensajes | Ahorra captura manual |
| PR-CALC | Cálculo | Calcula costos, márgenes, ratios, proyecciones o KPIs | Base para decisiones financieras |
| PR-VAL | Validación | Revisa si la información está completa y correcta | Reduce errores |
| PR-COMP | Comparación | Compara periodos, versiones, escenarios, proveedores o rutas | Mejora toma de decisiones |
| PR-SIM | Simulación | Modela escenarios futuros | Útil para estrategia, pricing y finanzas |
| PR-ANOM | Detección de anomalías | Encuentra datos raros o inconsistentes | Detecta fugas, errores o fraudes |
| PR-SUM | Resumen | Condensa información larga | Acelera decisiones |
| PR-PRIOR | Priorización | Ordena tareas o problemas por impacto | Enfoca al equipo humano |
| PR-RISK | Análisis de riesgo | Evalúa probabilidad, impacto y mitigación | Protege la empresa |
| PR-ROOT | Causa-raíz | Identifica origen de problemas | Mejora continua |
| PR-TRACE | Trazabilidad | Conecta dato, fuente, decisión y responsable | Aumenta control |
| PR-QA | Control de calidad | Revisa entregables contra criterios definidos | Evita outputs incorrectos |

---

## **5.3 Habilidades de salida y entregables**

| Código | Habilidad | Qué produce | Valor |
| :---- | :---- | :---- | :---- |
| OUT-REP | Reporte | Reportes financieros, operativos, comerciales o ejecutivos | Documenta resultados |
| OUT-BRIEF | Brief ejecutivo | Resumen corto para decisión | Reduce ruido para dirección |
| OUT-TABLE | Tabla | Comparativos, rankings, matrices y análisis numéricos | Facilita interpretación |
| OUT-DASH | Dashboard | Visualización de KPIs y semáforos | Da visibilidad continua |
| OUT-CHK | Checklist | Lista de validación o cierre | Reduce errores |
| OUT-ALERT | Alerta | Riesgo, vencimiento, desviación o evento crítico | Permite reaccionar rápido |
| OUT-DOC | Documento formal | Contratos, SOPs, políticas, propuestas o manuales | Estandariza |
| OUT-EMAIL | Email/mensaje | Comunicación lista para enviar | Ahorra tiempo comercial y operativo |
| OUT-PACK | Paquete documental | Conjunto de archivos listos para otro equipo | Facilita traspasos |
| OUT-REC | Recomendación | Siguiente acción sugerida | Convierte análisis en decisión |
| OUT-BIT | Bitácora | Registro de eventos, cambios o incidencias | Da trazabilidad |
| OUT-SCORE | Score | Calificación de cliente, candidato, agente o riesgo | Facilita priorización |

---

## **5.4 Habilidades de control y límites**

| Código | Habilidad | Qué hace |
| :---- | :---- | :---- |
| CTL-ESC | Escalamiento humano | Detecta cuándo debe intervenir una persona |
| CTL-HITL | Human-in-the-loop | Obliga revisión humana antes de acciones críticas |
| CTL-LIMIT | Límites de decisión | Define qué no puede aprobar solo |
| CTL-AUDIT | Auditoría | Registra quién hizo qué, cuándo y con qué fuente |
| CTL-REJECT | Rechazo/corrección | Devuelve entregables con errores |
| CTL-CONF | Confianza y certeza | Marca nivel de seguridad, supuestos y dudas |
| CTL-VERSION | Versionamiento | Controla cambios y versiones |
| CTL-POLICY | Cumplimiento de políticas internas | Revisa reglas de negocio y criterios |

---

# **6\. Capa central de orquestación**

## **O1. Agente Orquestador General**

**Misión:** coordinar toda la oficina virtual, activar departamentos, distribuir trabajo, integrar entregables y escalar decisiones humanas cuando sea necesario.

**Habilidades funcionales:**

* Orquestación multiagente.  
* Priorización general.  
* División de trabajo.  
* Gestión de dependencias.  
* Coordinación interdepartamental.  
* Integración de entregables.  
* Detección de bloqueos.  
* Escalamiento humano.  
* Control de flujo.  
* Supervisión general.

**Habilidades técnicas asignadas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-EMAIL, IN-ERP, IN-DASH, IN-DOCS.  
* PR-CLASS, PR-SUM, PR-PRIOR, PR-RISK, PR-TRACE, PR-QA.  
* OUT-BRIEF, OUT-REP, OUT-ALERT, OUT-REC, OUT-BIT.  
* CTL-ESC, CTL-HITL, CTL-LIMIT, CTL-AUDIT, CTL-CONF.

**Entradas:**

* Solicitudes humanas.  
* Objetivos estratégicos.  
* Datos del ERP.  
* Reportes departamentales.  
* Alertas críticas.  
* Requerimientos de clientes.  
* Incidencias.  
* Proyectos.

**Salidas:**

* Plan de trabajo.  
* Asignación de departamentos.  
* Flujo de ejecución.  
* Reporte integrado.  
* Recomendaciones.  
* Alertas de decisión humana.  
* Entregable final consolidado.

**Valor:** permite que la oficina funcione como un sistema coordinado y no como agentes aislados.

---

# **7\. Agentes líderes de departamento**

## **L1. Agente Líder de Dirección y Gobierno**

**Misión:** coordinar estrategia, gobierno corporativo, PMO, KPIs globales y reportes ejecutivos.

**Habilidades funcionales:**

* Estrategia.  
* Gobierno corporativo.  
* Seguimiento de acuerdos.  
* Análisis ejecutivo.  
* Gestión de proyectos.  
* Priorización.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DASH, IN-ERP, IN-DOCS.  
* PR-SUM, PR-PRIOR, PR-COMP, PR-RISK, PR-TRACE.  
* OUT-BRIEF, OUT-REP, OUT-DASH, OUT-ALERT, OUT-REC.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** objetivos, KPIs, proyectos, acuerdos, reportes departamentales.

**Salidas:** prioridades estratégicas, reportes ejecutivos, acuerdos, seguimiento de proyectos.

**Valor:** traduce información de alto nivel en dirección y prioridades.

---

## **L2. Agente Líder de Finanzas, Contabilidad y Administración**

**Misión:** coordinar planeación financiera, costos, tesorería, cobranza, pagos, fiscal, contabilidad y administración documental.

**Habilidades funcionales:**

* Análisis financiero.  
* Control presupuestal.  
* Flujo de caja.  
* Rentabilidad.  
* Fiscal.  
* Contabilidad.  
* Administración.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-PDF, IN-ERP, IN-DB, IN-DASH, IN-DOCS.  
* PR-CALC, PR-VAL, PR-COMP, PR-SIM, PR-ANOM, PR-QA.  
* OUT-REP, OUT-TABLE, OUT-DASH, OUT-ALERT, OUT-PACK.  
* CTL-ESC, CTL-HITL, CTL-AUDIT, CTL-CONF.

**Entradas:** ingresos, costos, gastos, facturas, pagos, presupuestos, estados financieros.

**Salidas:** reporte financiero, alertas de liquidez, análisis de rentabilidad, información para contador.

**Valor:** mantiene la salud financiera visible y controlada.

---

## **L3. Agente Líder de Operaciones Logísticas**

**Misión:** coordinar planeación, tráfico, flota, mantenimiento, combustible, evidencias, seguridad operativa e incidencias.

**Habilidades funcionales:**

* Operación logística.  
* Rutas.  
* Despacho.  
* Seguimiento.  
* Control de flota.  
* Cierre operativo.  
* Seguridad.

**Habilidades técnicas:**

* IN-TXT, IN-XLSX, IN-CSV, IN-IMG, IN-ERP, IN-GPS, IN-DOCS.  
* PR-CLASS, PR-VAL, PR-ANOM, PR-PRIOR, PR-RISK, PR-QA.  
* OUT-REP, OUT-CHK, OUT-ALERT, OUT-BIT, OUT-PACK.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** solicitudes de viaje, flota, operadores, rutas, GPS, evidencias, incidencias.

**Salidas:** operación programada, estatus operativo, cierres de viaje, alertas críticas.

**Valor:** reduce caos operativo y mejora control de ejecución.

---

## **L4. Agente Líder de Comercial y Cliente**

**Misión:** coordinar prospección, CRM, pricing, propuestas, customer success, atención al cliente y marketing.

**Habilidades funcionales:**

* Ventas.  
* Pricing.  
* CRM.  
* Cliente.  
* Marketing.  
* Retención.  
* Comunicación comercial.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-EMAIL, IN-ERP, IN-DASH.  
* PR-CLASS, PR-COMP, PR-CALC, PR-SUM, PR-PRIOR, PR-QA.  
* OUT-DOC, OUT-EMAIL, OUT-REP, OUT-TABLE, OUT-REC, OUT-SCORE.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** leads, solicitudes de cotización, historial de cliente, pipeline, tickets.

**Salidas:** oportunidades calificadas, cotizaciones, propuestas, reportes de cliente, alertas comerciales.

**Valor:** ayuda a vender mejor, con control de margen y seguimiento.

---

## **L5. Agente Líder de Tecnología, Datos e Innovación**

**Misión:** coordinar ERP, desarrollo, arquitectura técnica, datos, IA, automatización, QA técnico, IT y ciberseguridad.

**Habilidades funcionales:**

* Producto digital.  
* Arquitectura.  
* Desarrollo.  
* Datos.  
* IA.  
* Automatización.  
* Seguridad.  
* QA.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-CSV, IN-ERP, IN-DB, IN-API, IN-DASH.  
* PR-CLASS, PR-VAL, PR-COMP, PR-ANOM, PR-QA, PR-TRACE.  
* OUT-DOC, OUT-REP, OUT-DASH, OUT-CHK, OUT-BIT.  
* CTL-VERSION, CTL-AUDIT, CTL-ESC, CTL-LIMIT.

**Entradas:** requerimientos, backlog, bugs, datos, integraciones, tickets IT.

**Salidas:** especificaciones, módulos ERP, dashboards, automatizaciones, documentación técnica.

**Valor:** convierte la visión del negocio en sistemas, datos y automatización.

---

## **L6. Agente Líder de Legal, Compliance y Riesgos**

**Misión:** coordinar legal corporativo, contratos, compliance, permisos, riesgos, seguros, siniestros y auditoría interna.

**Habilidades funcionales:**

* Legal.  
* Contratos.  
* Cumplimiento.  
* Riesgos.  
* Auditoría.  
* Seguros.  
* Control documental.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-EMAIL, IN-ERP.  
* PR-EXT, PR-VAL, PR-COMP, PR-RISK, PR-TRACE, PR-QA.  
* OUT-REP, OUT-CHK, OUT-ALERT, OUT-DOC, OUT-PACK.  
* CTL-HITL, CTL-ESC, CTL-AUDIT, CTL-CONF.

**Entradas:** contratos, permisos, pólizas, documentos regulatorios, riesgos, siniestros.

**Salidas:** reportes legales, matriz de riesgos, alertas de cumplimiento, checklists de autorización.

**Valor:** protege a la empresa de errores legales, regulatorios y contractuales.

---

## **L7. Agente Líder de Talento y Cultura**

**Misión:** coordinar reclutamiento, onboarding, expedientes, nómina, compensaciones, capacitación, cultura y desempeño.

**Habilidades funcionales:**

* Talento.  
* Procesos laborales.  
* Capacitación.  
* Cultura.  
* Comunicación interna.  
* Desempeño.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DOCS, IN-EMAIL.  
* PR-CLASS, PR-EXT, PR-VAL, PR-SUM, PR-SCORE, PR-QA.  
* OUT-DOC, OUT-CHK, OUT-REP, OUT-SCORE, OUT-PACK.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** vacantes, candidatos, incidencias, evaluaciones, manuales, cultura.

**Salidas:** perfiles, rankings de candidatos, expedientes, pre-nómina, planes de capacitación.

**Valor:** profesionaliza talento sin necesitar un área humana grande desde el inicio.

---

## **L8. Agente Líder de Calidad, Procesos y Sostenibilidad**

**Misión:** coordinar calidad, SOPs, mejora continua, ESG, seguridad e higiene y auditoría de agentes IA.

**Habilidades funcionales:**

* Calidad.  
* Procesos.  
* Mejora continua.  
* Auditoría IA.  
* Sostenibilidad.  
* Seguridad laboral.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DASH, IN-DOCS, IN-ERP.  
* PR-CLASS, PR-VAL, PR-ROOT, PR-QA, PR-TRACE, PR-RISK.  
* OUT-DOC, OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-REJECT, CTL-AUDIT, CTL-VERSION, CTL-CONF.

**Entradas:** procesos, entregables, auditorías, errores, indicadores ESG, incidentes.

**Salidas:** SOPs, acciones correctivas, reportes de calidad, evaluación de agentes IA, reportes ESG.

**Valor:** evita que la empresa digital crezca desordenada o produzca errores a escala.

---

# **8\. Departamento 01: Dirección y Gobierno**

## **Propósito**

Dirigir la empresa digital, mantener orden corporativo, dar seguimiento a proyectos estratégicos y convertir información de toda la empresa en decisiones ejecutivas.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 1.1 Estrategia, Gobierno y PMO | 3 |
| 1.2 Inteligencia Ejecutiva y KPIs Globales | 2 |

---

## **Equipo 1.1 — Estrategia, Gobierno y PMO**

### **A1. Agente Estrategia y Decisión Ejecutiva**

**Misión:** apoyar a dirección en análisis estratégico, crecimiento, expansión y decisiones de alto impacto.

**Habilidades funcionales:**

* Análisis estratégico.  
* Análisis competitivo.  
* Expansión.  
* Escenarios.  
* Priorización.  
* Evaluación de oportunidades.  
* Recomendaciones ejecutivas.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DASH, IN-ERP.  
* PR-COMP, PR-SIM, PR-SUM, PR-PRIOR, PR-RISK.  
* OUT-BRIEF, OUT-REP, OUT-TABLE, OUT-REC.  
* CTL-ESC, CTL-CONF, CTL-HITL.

**Entradas:** objetivos, mercado, competidores, reportes internos, datos financieros, datos comerciales.

**Salidas:** análisis estratégico, escenarios, matriz de prioridades, recomendación ejecutiva.

**Valor:** ayuda a pensar como empresa global y decidir dónde enfocar recursos.

---

### **A2. Agente Gobierno Corporativo y PMO**

**Misión:** mantener orden institucional, acuerdos, proyectos, responsables y seguimiento.

**Habilidades funcionales:**

* Actas.  
* Acuerdos.  
* Políticas internas.  
* Seguimiento de decisiones.  
* Cronogramas.  
* Bloqueos.  
* Avance de proyectos.  
* Control de responsables.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-EMAIL, IN-DASH.  
* PR-CLASS, PR-EXT, PR-PRIOR, PR-TRACE, PR-QA.  
* OUT-DOC, OUT-BIT, OUT-REP, OUT-CHK, OUT-ALERT.  
* CTL-AUDIT, CTL-VERSION, CTL-ESC.

**Entradas:** reuniones, decisiones, proyectos, responsables, fechas compromiso, políticas.

**Salidas:** minutas, actas, matriz de acuerdos, reporte de avance, lista de bloqueos.

**Valor:** evita que las decisiones se pierdan y convierte acuerdos en seguimiento real.

---

### **A3. Agente Síntesis Ejecutiva**

**Misión:** traducir información compleja en reportes claros y accionables para dirección.

**Habilidades funcionales:**

* Resumen ejecutivo.  
* Daily brief.  
* Weekly review.  
* Preparación de juntas.  
* Priorización de información.  
* Comunicación ejecutiva.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DASH, IN-ERP, IN-EMAIL.  
* PR-SUM, PR-PRIOR, PR-CLASS, PR-RISK.  
* OUT-BRIEF, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-CONF, CTL-ESC.

**Entradas:** reportes departamentales, KPIs, alertas, minutas, proyectos, incidencias.

**Salidas:** daily brief, weekly business review, executive summary, agenda de dirección.

**Valor:** reduce ruido y permite que dirección vea lo más importante.

---

## **Equipo 1.2 — Inteligencia Ejecutiva y KPIs Globales**

### **A4. Agente Inteligencia Ejecutiva y KPIs**

**Misión:** consolidar indicadores globales para medir desempeño de toda la empresa.

**Habilidades funcionales:**

* Dashboard ejecutivo.  
* KPIs globales.  
* Scorecard empresarial.  
* Reportes directivos.  
* Análisis de desempeño.  
* Métricas por departamento.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DB, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SUM.  
* OUT-DASH, OUT-REP, OUT-TABLE, OUT-BRIEF.  
* CTL-TRACE, CTL-CONF.

**Entradas:** KPIs financieros, operativos, comerciales, talento, calidad y datos ERP.

**Salidas:** dashboard ejecutivo, scorecard, reporte mensual, diagnóstico de desempeño.

**Valor:** permite dirigir con datos, no con intuición.

---

### **A5. Agente Alertas Críticas y Prioridades**

**Misión:** detectar eventos críticos y ayudar a priorizar decisiones urgentes.

**Habilidades funcionales:**

* Alertas de liquidez.  
* Alertas operativas.  
* Alertas comerciales.  
* Alertas legales.  
* Riesgos críticos.  
* Priorización ejecutiva.  
* Semáforos.

**Habilidades técnicas:**

* IN-ERP, IN-DASH, IN-EMAIL, IN-GPS, IN-DOCS.  
* PR-ANOM, PR-RISK, PR-PRIOR, PR-VAL.  
* OUT-ALERT, OUT-BRIEF, OUT-REC, OUT-BIT.  
* CTL-ESC, CTL-HITL.

**Entradas:** alertas del ERP, incidencias, riesgos, datos financieros, datos operativos, tickets críticos.

**Salidas:** alertas priorizadas, semáforo ejecutivo, recomendación de acción, escalamiento.

**Valor:** permite reaccionar antes de que los problemas crezcan.

---

# **9\. Departamento 02: Finanzas, Contabilidad y Administración**

## **Propósito**

Controlar salud financiera, costos, rentabilidad, liquidez, obligaciones fiscales, registros contables y administración documental.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 2.1 Planeación y Análisis Financiero | 4 |
| 2.2 Costos y Rentabilidad Logística | 4 |
| 2.3 Tesorería, Cobranza y Pagos | 3 |
| 2.4 Contabilidad, Fiscal y Administración Documental | 3 |

---

## **Equipo 2.1 — Planeación y Análisis Financiero**

### **A6. Agente FP\&A y Forecast Financiero**

**Misión:** proyectar el futuro financiero de la empresa.

**Habilidades funcionales:**

* Forecast.  
* Presupuestos.  
* Escenarios.  
* Flujo proyectado.  
* Sensibilidad financiera.  
* Necesidades de capital.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-SIM, PR-COMP, PR-ANOM.  
* OUT-REP, OUT-TABLE, OUT-DASH, OUT-ALERT.  
* CTL-CONF, CTL-ESC.

**Entradas:** ventas, costos, gastos, pipeline, flota, rutas, presupuestos.

**Salidas:** forecast financiero, escenarios, presupuesto, alertas de capital, proyección de flujo.

**Valor:** permite anticipar necesidades de dinero antes de que se vuelvan urgencias.

---

### **A7. Agente Performance Financiero**

**Misión:** medir la salud financiera mediante indicadores y variaciones.

**Habilidades funcionales:**

* ROE.  
* ROA.  
* ROIC.  
* EBITDA.  
* Margen bruto.  
* Margen operativo.  
* Liquidez.  
* Endeudamiento.  
* Capital de trabajo.  
* Variaciones real vs presupuesto.  
* Variaciones real vs forecast.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SUM.  
* OUT-REP, OUT-TABLE, OUT-DASH, OUT-REC.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** estados financieros, presupuestos, flujo, deuda, activos, ingresos, gastos.

**Salidas:** reporte de performance, análisis de razones, alertas financieras, diagnóstico ejecutivo.

**Valor:** resume la salud financiera en indicadores accionables.

---

### **A8. Agente Estados Financieros y Cierre**

**Misión:** preparar estructura de estados financieros y apoyar el cierre mensual.

**Habilidades funcionales:**

* Estado de resultados.  
* Balance general.  
* Flujo de efectivo.  
* Cierre mensual.  
* Variaciones base.  
* Integración financiera.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-CSV, IN-ERP, IN-DOCS.  
* PR-EXT, PR-CALC, PR-VAL, PR-COMP.  
* OUT-REP, OUT-TABLE, OUT-PACK, OUT-CHK.  
* CTL-AUDIT, CTL-CONF.

**Entradas:** registros contables, facturas, pagos, cobros, bancos, gastos, activos.

**Salidas:** estado de resultados preliminar, balance preliminar, flujo de efectivo, paquete de cierre.

**Valor:** ayuda a tener cierres ordenados y comparables.

---

### **A9. Agente QA Financiero**

**Misión:** revisar consistencia, trazabilidad y calidad de reportes financieros.

**Habilidades funcionales:**

* Revisión de fórmulas.  
* Validación de supuestos.  
* Consistencia financiera.  
* Trazabilidad de datos.  
* Detección de errores.  
* Revisión de escenarios.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-ERP, IN-DASH.  
* PR-VAL, PR-QA, PR-ANOM, PR-TRACE.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-REJECT, CTL-AUDIT, CTL-CONF.

**Entradas:** reportes financieros, modelos, presupuestos, estados financieros, supuestos.

**Salidas:** reporte QA financiero, errores detectados, correcciones solicitadas, validación final.

**Valor:** evita que se tomen decisiones con cálculos o supuestos incorrectos.

---

## **Equipo 2.2 — Costos y Rentabilidad Logística**

### **A10. Agente Costos Logísticos**

**Misión:** construir la base de costos reales y estimados de la operación logística.

**Habilidades funcionales:**

* Costo por km.  
* Combustible.  
* Casetas.  
* Operador.  
* Mantenimiento.  
* Llantas.  
* Seguro.  
* Depreciación.  
* Costos fijos asignados.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-PDF.  
* PR-CALC, PR-COMP, PR-SIM, PR-VAL.  
* OUT-TABLE, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** rutas, km, combustible, nómina, mantenimiento, seguros, gastos fijos.

**Salidas:** costo por km, costo por viaje, matriz de costos, alertas de sobrecosto.

**Valor:** evita vender servicios sin saber si realmente dejan margen.

---

### **A11. Agente Rentabilidad Logística**

**Misión:** analizar rentabilidad por viaje, ruta, cliente, unidad y operador.

**Habilidades funcionales:**

* Margen por viaje.  
* Rentabilidad por ruta.  
* Rentabilidad por cliente.  
* Rentabilidad por unidad.  
* Rentabilidad por operador.  
* Margen por servicio.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SUM.  
* OUT-REP, OUT-TABLE, OUT-DASH, OUT-ALERT.  
* CTL-CONF, CTL-ESC.

**Entradas:** ingresos, costos, viajes, rutas, clientes, unidades, operadores.

**Salidas:** reporte de rentabilidad, ranking de rutas, ranking de clientes, alertas de margen.

**Valor:** detecta qué clientes, rutas o unidades parecen buenos pero destruyen margen.

---

### **A12. Agente Simulación de Escenarios y Margen**

**Misión:** modelar escenarios de precio y margen para apoyar decisiones comerciales y financieras.

**Habilidades funcionales:**

* Escenario mínimo.  
* Escenario óptimo.  
* Escenario objetivo.  
* Sensibilidad por combustible.  
* Sensibilidad por distancia.  
* Sensibilidad por precio.  
* Punto de equilibrio.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP.  
* PR-SIM, PR-CALC, PR-COMP, PR-RISK.  
* OUT-TABLE, OUT-REP, OUT-REC, OUT-ALERT.  
* CTL-CONF, CTL-HITL.

**Entradas:** costos, rutas, tarifas, clientes, volumen, riesgo, precio objetivo.

**Salidas:** escenarios de margen, precio sugerido, punto de equilibrio, recomendación comercial.

**Valor:** permite decidir precios con escenarios y no con corazonadas.

---

### **A13. Agente QA de Costos y Rentabilidad**

**Misión:** revisar que los cálculos de costos y márgenes sean correctos.

**Habilidades funcionales:**

* Validación de costos.  
* Validación de márgenes.  
* Validación de supuestos.  
* Costo real vs estimado.  
* Alertas de margen negativo.  
* Revisión cruzada.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-VAL, PR-QA, PR-ANOM, PR-TRACE.  
* OUT-CHK, OUT-REP, OUT-ALERT.  
* CTL-REJECT, CTL-CONF.

**Entradas:** costeo, rentabilidad, simulaciones, rutas, supuestos.

**Salidas:** validación de costos, errores detectados, comentarios de corrección, aprobación QA.

**Valor:** evita cotizar con costos mal calculados.

---

## **Equipo 2.3 — Tesorería, Cobranza y Pagos**

### **A14. Agente Tesorería y Liquidez**

**Misión:** controlar caja, bancos y liquidez diaria.

**Habilidades funcionales:**

* Posición de caja.  
* Bancos.  
* Flujo diario.  
* Flujo semanal.  
* Días de caja.  
* Prioridad de pagos.  
* Alertas de liquidez.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-PRIOR.  
* OUT-REP, OUT-TABLE, OUT-ALERT, OUT-REC.  
* CTL-ESC, CTL-HITL.

**Entradas:** bancos, pagos, cobros, facturas, nómina, gastos fijos.

**Salidas:** cash position, flujo semanal, alertas de liquidez, calendario de caja.

**Valor:** evita que la empresa sea rentable en papel pero se quede sin efectivo.

---

### **A15. Agente Cobranza y Cartera**

**Misión:** acelerar cobros y controlar cartera vencida.

**Habilidades funcionales:**

* Cuentas por cobrar.  
* Aging de cartera.  
* Facturas vencidas.  
* Seguimiento de clientes.  
* Promesas de pago.  
* Riesgo de morosidad.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-EMAIL.  
* PR-CLASS, PR-COMP, PR-PRIOR, PR-ANOM.  
* OUT-REP, OUT-TABLE, OUT-EMAIL, OUT-ALERT.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** facturas, clientes, pagos, fechas de vencimiento, historial.

**Salidas:** reporte de cartera, alertas de vencimiento, lista de cobranza, flujo esperado.

**Valor:** convierte cobranza en un proceso activo, no reactivo.

---

### **A16. Agente Cuentas por Pagar y Proveedores**

**Misión:** controlar obligaciones con proveedores y programar pagos.

**Habilidades funcionales:**

* Cuentas por pagar.  
* Facturas de proveedor.  
* Vencimientos.  
* Priorización de pagos.  
* Comprobantes.  
* Conciliación con proveedores.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-ERP, IN-DOCS, IN-EMAIL.  
* PR-EXT, PR-VAL, PR-PRIOR, PR-COMP.  
* OUT-TABLE, OUT-REP, OUT-CHK, OUT-ALERT.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** facturas, proveedores, contratos, órdenes de compra, bancos.

**Salidas:** reporte CXP, calendario de pagos, facturas pendientes, alertas de vencimiento.

**Valor:** ayuda a pagar ordenadamente sin comprometer liquidez.

---

## **Equipo 2.4 — Contabilidad, Fiscal y Administración Documental**

### **A17. Agente Contable y Cierre Administrativo**

**Misión:** ordenar registros contables y apoyar cierres administrativos.

**Habilidades funcionales:**

* Clasificación contable.  
* Conciliación documental.  
* Cierre administrativo.  
* Control de gastos.  
* Archivo contable.  
* Soporte de pólizas.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-CSV, IN-DOCS, IN-ERP.  
* PR-CLASS, PR-EXT, PR-VAL, PR-COMP.  
* OUT-PACK, OUT-CHK, OUT-REP, OUT-TABLE.  
* CTL-AUDIT, CTL-CONF.

**Entradas:** facturas, recibos, pagos, cobros, gastos, bancos.

**Salidas:** paquete contable, conciliaciones preliminares, checklist de cierre, faltantes.

**Valor:** reduce carga del contador y mejora orden documental.

---

### **A18. Agente Fiscal, CFDI y Carta Porte**

**Misión:** apoyar cumplimiento fiscal y documentación electrónica.

**Habilidades funcionales:**

* CFDI.  
* Carta Porte.  
* IVA.  
* ISR.  
* Deducibilidad.  
* Validación fiscal.  
* Alertas fiscales.  
* Paquete para contador.

**Habilidades técnicas:**

* IN-PDF, IN-XLSX, IN-CSV, IN-DOCS, IN-ERP.  
* PR-EXT, PR-VAL, PR-COMP, PR-RISK, PR-QA.  
* OUT-CHK, OUT-PACK, OUT-ALERT, OUT-REP.  
* CTL-HITL, CTL-ESC, CTL-AUDIT.

**Entradas:** facturas, viajes, clientes, proveedores, datos fiscales, documentos operativos.

**Salidas:** reporte CFDI, alertas fiscales, paquete fiscal, inconsistencias detectadas.

**Valor:** reduce riesgos fiscales y errores en documentación crítica.

---

### **A19. Agente Administración Documental**

**Misión:** mantener orden digital de documentos administrativos, contables y fiscales.

**Habilidades funcionales:**

* Archivo digital.  
* Expedientes.  
* Control documental.  
* Checklists.  
* Paquetes para contador.  
* Paquetes para auditoría.  
* Versionamiento documental.

**Habilidades técnicas:**

* IN-PDF, IN-XLSX, IN-DOCS, IN-IMG, IN-EMAIL.  
* PR-CLASS, PR-EXT, PR-VAL, PR-TRACE.  
* OUT-PACK, OUT-CHK, OUT-DOC, OUT-ALERT.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** documentos, facturas, contratos, comprobantes, archivos internos.

**Salidas:** expedientes completos, archivos organizados, checklists, paquetes documentales.

**Valor:** crea memoria documental para la empresa y evita pérdidas de información.

---

# **10\. Departamento 03: Operaciones Logísticas**

## **Propósito**

Planear, ejecutar, monitorear y cerrar operaciones logísticas con control de rutas, flota, tráfico, seguridad, combustible, evidencias e incidencias.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 3.1 Planeación, Rutas y Programación | 3 |
| 3.2 Tráfico, Torre de Control e Incidencias | 4 |
| 3.3 Flota, Mantenimiento y Combustible | 3 |
| 3.4 Evidencias, Documentación y Cierre Operativo | 3 |
| 3.5 Seguridad Operativa y Riesgo en Ruta | 3 |

---

## **Equipo 3.1 — Planeación, Rutas y Programación**

### **A20. Agente Planeación Operativa**

**Misión:** estructurar la programación operativa de viajes.

**Habilidades funcionales:**

* Programación de viajes.  
* Ventanas de carga.  
* Ventanas de descarga.  
* Secuencia operativa.  
* Calendario operativo.  
* Confirmación previa.

**Habilidades técnicas:**

* IN-TXT, IN-XLSX, IN-ERP, IN-EMAIL, IN-DASH.  
* PR-CLASS, PR-VAL, PR-PRIOR, PR-COMP.  
* OUT-CHK, OUT-BIT, OUT-REP, OUT-ALERT.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** solicitudes de servicio, disponibilidad, cliente, horarios, capacidad.

**Salidas:** viaje programado, calendario operativo, checklist previo, programación diaria.

**Valor:** convierte solicitudes en operación planificada.

---

### **A21. Agente Rutas, Tiempos y Costos Operativos**

**Misión:** estimar rutas, tiempos y costos operativos preliminares.

**Habilidades funcionales:**

* Distancia.  
* ETA.  
* Ruta principal.  
* Ruta alternativa.  
* Casetas.  
* Riesgo preliminar.  
* Costo estimado.

**Habilidades técnicas:**

* IN-TXT, IN-XLSX, IN-CSV, IN-ERP, IN-GPS.  
* PR-CALC, PR-COMP, PR-SIM, PR-RISK.  
* OUT-TABLE, OUT-REP, OUT-REC, OUT-ALERT.  
* CTL-CONF, CTL-ESC.

**Entradas:** origen, destino, tipo de carga, unidad, horarios, datos de ruta.

**Salidas:** ruta sugerida, ruta alternativa, tiempo estimado, costo operativo, riesgo preliminar.

**Valor:** mejora decisiones de operación y pricing.

---

### **A22. Agente Capacidad Flota-Operador**

**Misión:** validar disponibilidad y compatibilidad de unidades y operadores.

**Habilidades funcionales:**

* Disponibilidad de unidades.  
* Disponibilidad de operadores.  
* Restricciones.  
* Compatibilidad unidad-servicio.  
* Compatibilidad operador-ruta.  
* Uso de capacidad.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-VAL, PR-COMP, PR-PRIOR, PR-ANOM.  
* OUT-TABLE, OUT-CHK, OUT-ALERT, OUT-REC.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** flota, operadores, agenda, restricciones, mantenimiento, horarios.

**Salidas:** unidad sugerida, operador sugerido, capacidad disponible, alertas de falta de capacidad.

**Valor:** evita comprometer viajes sin recursos disponibles.

---

## **Equipo 3.2 — Tráfico, Torre de Control e Incidencias**

### **A23. Agente Dispatch y Seguimiento Operativo**

**Misión:** coordinar salida, carga, descarga, estatus y bitácora de viaje.

**Habilidades funcionales:**

* Salida de unidad.  
* Confirmación de carga.  
* Confirmación de descarga.  
* Estatus operativo.  
* Bitácora.  
* Cierre preliminar.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-ERP, IN-GPS, IN-DOCS.  
* PR-CLASS, PR-VAL, PR-TRACE, PR-PRIOR.  
* OUT-BIT, OUT-REP, OUT-CHK, OUT-ALERT.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** viaje programado, unidad, operador, cliente, ruta, horarios.

**Salidas:** estatus de viaje, bitácora actualizada, confirmaciones operativas.

**Valor:** mantiene control minuto a minuto del viaje.

---

### **A24. Agente Torre de Control**

**Misión:** monitorear operación en tiempo real.

**Habilidades funcionales:**

* GPS.  
* ETA.  
* Alertas de retraso.  
* Alertas de desvío.  
* Paradas no autorizadas.  
* Semáforo operativo.

**Habilidades técnicas:**

* IN-GPS, IN-ERP, IN-DASH, IN-CSV.  
* PR-ANOM, PR-VAL, PR-COMP, PR-RISK.  
* OUT-ALERT, OUT-DASH, OUT-BIT, OUT-REP.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** GPS, ruta, horario, posición, bitácora, parámetros de seguridad.

**Salidas:** tracking, ETA, alertas, semáforo operativo, reporte de desviaciones.

**Valor:** permite anticiparse a retrasos, desvíos y riesgos.

---

### **A25. Agente Incidencias y Escalamiento**

**Misión:** gestionar problemas operativos y escalar según severidad.

**Habilidades funcionales:**

* Registro de incidencia.  
* Severidad.  
* Acción correctiva.  
* Escalamiento.  
* Comunicación interna.  
* Lección aprendida.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-GPS, IN-IMG, IN-ERP.  
* PR-CLASS, PR-RISK, PR-PRIOR, PR-ROOT, PR-TRACE.  
* OUT-BIT, OUT-ALERT, OUT-REP, OUT-REC.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** alertas, operador, cliente, tráfico, GPS, reportes.

**Salidas:** reporte de incidencia, plan de acción, escalamiento, cierre de incidencia.

**Valor:** convierte problemas en procesos controlados y documentados.

---

### **A26. Agente Comunicación Operativa**

**Misión:** mantener comunicación clara entre operación, operador, cliente y áreas internas.

**Habilidades funcionales:**

* Avisos preventivos.  
* Notificaciones.  
* Comunicación con operador.  
* Comunicación con cliente.  
* Resúmenes de estatus.  
* Registro de comunicaciones.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-ERP, IN-DASH.  
* PR-SUM, PR-CLASS, PR-PRIOR, PR-TRACE.  
* OUT-EMAIL, OUT-BIT, OUT-ALERT, OUT-BRIEF.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** estatus, incidencias, ETA, instrucciones, cliente, operador.

**Salidas:** mensajes operativos, updates al cliente, comunicados internos, historial de comunicación.

**Valor:** reduce incertidumbre y mejora experiencia del cliente.

---

## **Equipo 3.3 — Flota, Mantenimiento y Combustible**

### **A27. Agente Flota y Documentos Vehiculares**

**Misión:** controlar unidades, disponibilidad y documentos vehiculares.

**Habilidades funcionales:**

* Alta de unidades.  
* Estado de flota.  
* Documentos vehiculares.  
* Vigencias.  
* Seguros.  
* Verificaciones.  
* Placas.  
* Disponibilidad.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-DOCS, IN-ERP, IN-DASH.  
* PR-CLASS, PR-VAL, PR-ANOM, PR-TRACE.  
* OUT-TABLE, OUT-CHK, OUT-ALERT, OUT-PACK.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** datos de unidad, pólizas, permisos, verificaciones, placas, mantenimiento.

**Salidas:** estado de flota, alertas de vigencia, expediente vehicular, disponibilidad.

**Valor:** evita que una unidad no pueda operar por falta de documentos.

---

### **A28. Agente Mantenimiento, Llantas y Refacciones**

**Misión:** reducir fallas mediante mantenimiento preventivo y correctivo.

**Habilidades funcionales:**

* Mantenimiento preventivo.  
* Mantenimiento correctivo.  
* Historial mecánico.  
* Talleres.  
* Refacciones.  
* Llantas.  
* Alertas de servicio.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-IMG, IN-ERP, IN-DASH.  
* PR-CLASS, PR-CALC, PR-ANOM, PR-ROOT, PR-PRIOR.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** km, reportes de operador, taller, historial, refacciones, calendario.

**Salidas:** calendario de mantenimiento, reporte de fallas, historial mecánico, alertas preventivas.

**Valor:** reduce fallas en carretera y tiempo fuera de operación.

---

### **A29. Agente Combustible y Rendimiento**

**Misión:** controlar consumo de combustible, anomalías y rendimiento.

**Habilidades funcionales:**

* Cargas.  
* Tickets.  
* Km/litro.  
* Consumo esperado.  
* Anomalías.  
* Costo por km.  
* Ranking de rendimiento.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-IMG, IN-ERP, IN-GPS.  
* PR-CALC, PR-COMP, PR-ANOM, PR-VAL.  
* OUT-REP, OUT-TABLE, OUT-ALERT, OUT-DASH.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** tickets, km, rutas, unidad, operador, precio combustible.

**Salidas:** reporte de rendimiento, alertas de consumo, costo combustible por km, ranking.

**Valor:** controla uno de los costos más importantes del transporte.

---

## **Equipo 3.4 — Evidencias, Documentación y Cierre Operativo**

### **A30. Agente Evidencias, POD y Documentos de Viaje**

**Misión:** recolectar y organizar evidencias de entrega y documentos del viaje.

**Habilidades funcionales:**

* POD.  
* Evidencia fotográfica.  
* Documentos de carga.  
* Documentos de descarga.  
* Archivo de viaje.  
* Checklist documental.

**Habilidades técnicas:**

* IN-IMG, IN-PDF, IN-DOCS, IN-EMAIL, IN-ERP.  
* PR-EXT, PR-CLASS, PR-VAL, PR-TRACE.  
* OUT-PACK, OUT-CHK, OUT-BIT, OUT-ALERT.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** fotos, POD, documentos de carga, Carta Porte, bitácora, cliente.

**Salidas:** paquete documental del viaje, evidencias validadas, checklist de faltantes.

**Valor:** permite cerrar viajes y facturar sin retrasos.

---

### **A31. Agente Cierre Operativo y Paquete de Facturación**

**Misión:** cerrar viaje operativamente y preparar traspaso a facturación.

**Habilidades funcionales:**

* Cierre de viaje.  
* Validación de bitácora.  
* Integración de evidencias.  
* Paquete de facturación.  
* Pendientes.  
* Traspaso a finanzas.

**Habilidades técnicas:**

* IN-PDF, IN-XLSX, IN-DOCS, IN-ERP.  
* PR-VAL, PR-CLASS, PR-TRACE, PR-QA.  
* OUT-PACK, OUT-CHK, OUT-BIT, OUT-REP.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** bitácora, evidencias, costos, documentos, incidencias.

**Salidas:** viaje cerrado, paquete para facturación, pendientes, estatus final.

**Valor:** conecta operaciones con facturación y cobranza.

---

### **A32. Agente QA Documental Operativo**

**Misión:** revisar documentación operativa antes de facturación.

**Habilidades funcionales:**

* Revisión documental.  
* Faltantes.  
* Checklist.  
* Rechazo por error.  
* Liberación documental.  
* Validación contra cliente.

**Habilidades técnicas:**

* IN-PDF, IN-IMG, IN-DOCS, IN-ERP.  
* PR-VAL, PR-QA, PR-TRACE, PR-ANOM.  
* OUT-CHK, OUT-ALERT, OUT-REP, OUT-REC.  
* CTL-REJECT, CTL-AUDIT.

**Entradas:** paquete documental, checklist, requerimientos del cliente, requisitos fiscales.

**Salidas:** aprobación documental, correcciones, reporte de errores, liberación.

**Valor:** reduce errores antes de emitir facturas o reclamar pagos.

---

## **Equipo 3.5 — Seguridad Operativa y Riesgo en Ruta**

### **A33. Agente Riesgo de Ruta y Protocolos**

**Misión:** evaluar riesgo de ruta y definir protocolos preventivos.

**Habilidades funcionales:**

* Clasificación de riesgo.  
* Horarios recomendados.  
* Zonas críticas.  
* Protocolos.  
* Recomendaciones preventivas.  
* Semáforo de ruta.

**Habilidades técnicas:**

* IN-TXT, IN-XLSX, IN-GPS, IN-ERP, IN-DASH.  
* PR-RISK, PR-COMP, PR-PRIOR, PR-SIM.  
* OUT-REP, OUT-CHK, OUT-ALERT, OUT-REC.  
* CTL-ESC, CTL-HITL.

**Entradas:** ruta, historial, tipo de carga, horario, zonas de riesgo.

**Salidas:** evaluación de riesgo, protocolo de ruta, recomendaciones, semáforo.

**Valor:** reduce exposición a robo, accidentes o eventos críticos.

---

### **A34. Agente Seguridad en Tránsito**

**Misión:** vigilar cumplimiento de protocolo durante el viaje.

**Habilidades funcionales:**

* Paradas no autorizadas.  
* Desvíos.  
* Alertas de riesgo.  
* Monitoreo de protocolo.  
* Validación de ruta segura.  
* Seguimiento de seguridad.

**Habilidades técnicas:**

* IN-GPS, IN-ERP, IN-DASH, IN-EMAIL.  
* PR-ANOM, PR-RISK, PR-VAL, PR-TRACE.  
* OUT-ALERT, OUT-BIT, OUT-REP.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** GPS, protocolo, ruta autorizada, bitácora, operador.

**Salidas:** alertas de seguridad, reporte de protocolo, incidencias de seguridad.

**Valor:** mantiene vigilancia preventiva durante operación real.

---

### **A35. Agente Incidentes Críticos y Reporte de Seguridad**

**Misión:** documentar y escalar accidentes, robos, amenazas o eventos críticos.

**Habilidades funcionales:**

* Robo.  
* Accidente.  
* Amenaza.  
* Línea de tiempo.  
* Evidencias.  
* Recomendaciones.  
* Reporte crítico.

**Habilidades técnicas:**

* IN-TXT, IN-IMG, IN-GPS, IN-DOCS, IN-EMAIL.  
* PR-EXT, PR-RISK, PR-TRACE, PR-ROOT.  
* OUT-REP, OUT-PACK, OUT-BIT, OUT-ALERT.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** alertas, operador, GPS, fotos, llamadas, reportes.

**Salidas:** reporte crítico, línea de tiempo, evidencia, recomendaciones preventivas.

**Valor:** permite responder profesionalmente ante eventos graves.

---

# **11\. Departamento 04: Comercial y Cliente**

## **Propósito**

Generar oportunidades, convertir clientes, construir marca, cotizar con rentabilidad, atender cuentas y retener clientes.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 4.1 Prospección, CRM y Pipeline | 2 |
| 4.2 Pricing, Cotizaciones y Propuestas | 3 |
| 4.3 Customer Success y Atención al Cliente | 3 |
| 4.4 Marketing, Marca y Comunicación Comercial | 3 |

---

## **Equipo 4.1 — Prospección, CRM y Pipeline**

### **A36. Agente Prospección e Inteligencia Comercial**

**Misión:** identificar oportunidades comerciales y clientes potenciales.

**Habilidades funcionales:**

* Prospección.  
* Research de empresas.  
* Decisores.  
* Industrias objetivo.  
* Perfil de cliente ideal.  
* Calificación de oportunidad.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-CSV, IN-EMAIL.  
* PR-CLASS, PR-SUM, PR-COMP, PR-SCORE.  
* OUT-TABLE, OUT-REP, OUT-SCORE, OUT-REC.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** industria objetivo, zona, tipo de cliente, servicios, mercado.

**Salidas:** lista de prospectos, perfil de cliente, contactos clave, score comercial.

**Valor:** alimenta ventas con oportunidades organizadas y priorizadas.

---

### **A37. Agente CRM, Pipeline y Seguimiento**

**Misión:** mantener orden comercial y seguimiento de oportunidades.

**Habilidades funcionales:**

* Pipeline.  
* Etapas comerciales.  
* Seguimientos.  
* Recordatorios.  
* Probabilidad de cierre.  
* Forecast comercial.

**Habilidades técnicas:**

* IN-ERP, IN-EMAIL, IN-XLSX, IN-DASH.  
* PR-CLASS, PR-PRIOR, PR-COMP, PR-SUM.  
* OUT-DASH, OUT-REP, OUT-ALERT, OUT-EMAIL.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** leads, reuniones, cotizaciones, historial, notas comerciales.

**Salidas:** pipeline actualizado, próximas acciones, forecast comercial, alertas de seguimiento.

**Valor:** evita perder oportunidades por falta de seguimiento.

---

## **Equipo 4.2 — Pricing, Cotizaciones y Propuestas**

### **A38. Agente Pricing, Costeo y Margen Comercial**

**Misión:** crear tarifas rentables y competitivas.

**Habilidades funcionales:**

* Solicitud comercial.  
* Costeo.  
* Precio.  
* Margen.  
* Descuento máximo.  
* Tarifa sugerida.  
* Aprobación preliminar.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-SIM, PR-RISK.  
* OUT-TABLE, OUT-REC, OUT-ALERT, OUT-REP.  
* CTL-HITL, CTL-CONF.

**Entradas:** ruta, costos, cliente, volumen, servicio, margen objetivo.

**Salidas:** precio sugerido, margen estimado, descuento máximo, justificación de tarifa.

**Valor:** protege margen sin perder competitividad.

---

### **A39. Agente Cotizaciones y Propuestas Comerciales**

**Misión:** convertir análisis comercial en documentos profesionales para cliente.

**Habilidades funcionales:**

* Cotización formal.  
* Propuesta PDF.  
* Presentación.  
* Correo comercial.  
* Argumentario.  
* Diferenciadores.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DOCS.  
* PR-SUM, PR-CLASS, PR-COMP, PR-VAL.  
* OUT-DOC, OUT-EMAIL, OUT-PACK, OUT-REP.  
* CTL-VERSION, CTL-CONF.

**Entradas:** precio, servicio, cliente, condiciones, beneficios, marca.

**Salidas:** cotización, propuesta comercial, email de envío, presentación.

**Valor:** mejora profesionalismo comercial y tasa de conversión.

---

### **A40. Agente QA Comercial**

**Misión:** revisar que cotizaciones y propuestas sean correctas antes de enviarse.

**Habilidades funcionales:**

* Validación de precio.  
* Validación de margen.  
* Revisión de datos.  
* Revisión de redacción.  
* Consistencia con cliente.  
* Checklist comercial.

**Habilidades técnicas:**

* IN-PDF, IN-XLSX, IN-DOCS, IN-ERP.  
* PR-VAL, PR-QA, PR-COMP, PR-ANOM.  
* OUT-CHK, OUT-ALERT, OUT-REC, OUT-REP.  
* CTL-REJECT, CTL-HITL, CTL-AUDIT.

**Entradas:** cotización, propuesta, precio, margen, datos cliente.

**Salidas:** aprobación QA, correcciones, checklist comercial, riesgo detectado.

**Valor:** evita enviar cotizaciones con errores, márgenes negativos o promesas imposibles.

---

## **Equipo 4.3 — Customer Success y Atención al Cliente**

### **A41. Agente Atención, Tickets y Escalamiento**

**Misión:** registrar, clasificar y escalar solicitudes o problemas de clientes.

**Habilidades funcionales:**

* Tickets.  
* Clasificación.  
* Respuesta inicial.  
* Escalamiento.  
* Cierre.  
* Historial de caso.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-ERP, IN-DASH.  
* PR-CLASS, PR-PRIOR, PR-SUM, PR-TRACE.  
* OUT-EMAIL, OUT-BIT, OUT-ALERT, OUT-REP.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** mensajes de cliente, llamadas, correos, incidencias, quejas.

**Salidas:** ticket, respuesta sugerida, escalamiento, cierre de caso.

**Valor:** da seguimiento ordenado a problemas y solicitudes.

---

### **A42. Agente Customer Success y Reportes de Servicio**

**Misión:** mantener satisfacción del cliente mediante seguimiento y reportes.

**Habilidades funcionales:**

* Desempeño por cliente.  
* Revisión mensual.  
* Indicadores.  
* Seguimiento.  
* Comunicación de resultados.  
* Reporte de servicio.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH, IN-EMAIL.  
* PR-CALC, PR-COMP, PR-SUM, PR-ANOM.  
* OUT-REP, OUT-DASH, OUT-EMAIL, OUT-BRIEF.  
* CTL-CONF, CTL-ESC.

**Entradas:** viajes, entregas, incidencias, cumplimiento, cliente, SLA.

**Salidas:** reporte de servicio, análisis de cuenta, plan de seguimiento.

**Valor:** convierte operación en confianza para el cliente.

---

### **A43. Agente Retención, Satisfacción y Expansión**

**Misión:** detectar riesgo de pérdida y oportunidades de crecimiento por cliente.

**Habilidades funcionales:**

* Satisfacción.  
* Quejas.  
* Riesgo de churn.  
* Upsell.  
* Plan de retención.  
* Expansión de cuenta.

**Habilidades técnicas:**

* IN-ERP, IN-DASH, IN-EMAIL, IN-XLSX.  
* PR-COMP, PR-RISK, PR-ANOM, PR-SCORE.  
* OUT-REP, OUT-ALERT, OUT-REC, OUT-SCORE.  
* CTL-ESC, CTL-CONF.

**Entradas:** tickets, quejas, desempeño, volumen, historial comercial.

**Salidas:** alerta de churn, oportunidad de expansión, plan de retención, reporte de satisfacción.

**Valor:** ayuda a conservar y crecer clientes.

---

## **Equipo 4.4 — Marketing, Marca y Comunicación Comercial**

### **A44. Agente Marca, Posicionamiento y Contenido**

**Misión:** construir narrativa de marca y contenido estratégico.

**Habilidades funcionales:**

* Branding.  
* Voz de marca.  
* Contenido.  
* Redes.  
* Storytelling.  
* Posicionamiento.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-DASH.  
* PR-SUM, PR-COMP, PR-CLASS, PR-PRIOR.  
* OUT-DOC, OUT-EMAIL, OUT-REP, OUT-REC.  
* CTL-VERSION, CTL-CONF.

**Entradas:** estrategia, servicios, mercado, clientes, diferenciadores.

**Salidas:** calendario de contenido, copies, mensajes de marca, ideas de campaña.

**Valor:** posiciona la empresa como moderna, confiable y tecnológica.

---

### **A45. Agente Campañas y Growth Marketing**

**Misión:** generar demanda mediante campañas y acciones de crecimiento.

**Habilidades funcionales:**

* Campañas.  
* Landing pages.  
* SEO básico.  
* Ads.  
* Leads.  
* Conversiones.  
* Performance de marketing.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-DASH, IN-ERP.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SCORE.  
* OUT-REP, OUT-DASH, OUT-REC, OUT-ALERT.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** objetivos, presupuesto, audiencia, propuesta de valor, métricas.

**Salidas:** campaña, reporte de performance, leads, recomendaciones.

**Valor:** convierte marca en oportunidades comerciales.

---

### **A46. Agente Diseño y Material Comercial**

**Misión:** producir materiales visuales y comerciales de venta.

**Habilidades funcionales:**

* Presentaciones.  
* One-pagers.  
* Brochures.  
* Diseño de propuestas.  
* Piezas comerciales.  
* Material para ventas.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-IMG.  
* PR-SUM, PR-VAL, PR-COMP.  
* OUT-DOC, OUT-PACK, OUT-REP.  
* CTL-VERSION, CTL-QA.

**Entradas:** marca, contenido, propuesta, servicios, cliente.

**Salidas:** presentación, brochure, one-pager, pieza comercial, material visual.

**Valor:** aumenta percepción de profesionalismo y confianza.

---

# **12\. Departamento 05: Tecnología, Datos e Innovación**

## **Propósito**

Construir y mantener el ERP, los sistemas internos, automatizaciones, datos, dashboards, arquitectura técnica y agentes IA.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 5.1 Producto ERP y Arquitectura Funcional | 3 |
| 5.2 Diseño, Frontend y Experiencia de Usuario | 3 |
| 5.3 Backend, Base de Datos e Integraciones | 4 |
| 5.4 QA, DevOps y Documentación Técnica | 4 |
| 5.5 Data, BI e Inteligencia Artificial | 5 |
| 5.6 IT, Ciberseguridad y Soporte Interno | 3 |

---

## **Equipo 5.1 — Producto ERP y Arquitectura Funcional**

### **A47. Agente Product Owner ERP**

**Misión:** definir qué módulos se construyen y por qué.

**Habilidades funcionales:**

* Product roadmap.  
* Priorización.  
* Módulos.  
* Valor de negocio.  
* Decisiones de producto.  
* Secuencia de construcción.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-ERP, IN-DASH.  
* PR-CLASS, PR-PRIOR, PR-COMP, PR-SUM.  
* OUT-DOC, OUT-REP, OUT-REC, OUT-BRIEF.  
* CTL-VERSION, CTL-HITL.

**Entradas:** procesos, necesidades de áreas, estrategia, feedback, errores.

**Salidas:** roadmap ERP, prioridades, definición de módulos, decisiones de producto.

**Valor:** asegura que el ERP se construya con lógica de negocio real.

---

### **A48. Agente Requerimientos y Procesos Funcionales**

**Misión:** convertir necesidades de negocio en requerimientos funcionales claros.

**Habilidades funcionales:**

* Requerimientos.  
* Historias de usuario.  
* Criterios de aceptación.  
* Flujos funcionales.  
* Casos de uso.  
* Reglas de negocio.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-ERP.  
* PR-EXT, PR-CLASS, PR-VAL, PR-TRACE.  
* OUT-DOC, OUT-CHK, OUT-REP.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** entrevistas, procesos, necesidades, usuarios, flujos actuales.

**Salidas:** requerimientos, historias de usuario, criterios de aceptación, flujos funcionales.

**Valor:** evita construir sistemas que no resuelven problemas reales.

---

### **A49. Agente Documentación Funcional y Backlog**

**Misión:** mantener trazabilidad funcional del ERP.

**Habilidades funcionales:**

* Backlog.  
* Documentación funcional.  
* Control de cambios.  
* Changelog funcional.  
* Manuales de usuario.  
* Matriz de requerimientos.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-ERP, IN-DASH.  
* PR-CLASS, PR-TRACE, PR-VAL, PR-SUM.  
* OUT-DOC, OUT-CHK, OUT-BIT, OUT-REP.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** requerimientos, cambios, releases, feedback, módulos.

**Salidas:** backlog actualizado, documentación funcional, changelog, manuales.

**Valor:** evita que el ERP dependa de memoria humana.

---

## **Equipo 5.2 — Diseño, Frontend y Experiencia de Usuario**

### **A50. Agente UX/UI y Flujos de Usuario**

**Misión:** diseñar experiencias claras y fáciles de usar.

**Habilidades funcionales:**

* UX.  
* Flujos.  
* Wireframes.  
* Prototipos.  
* Usabilidad.  
* Accesibilidad básica.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-IMG.  
* PR-CLASS, PR-COMP, PR-VAL, PR-SUM.  
* OUT-DOC, OUT-CHK, OUT-REC.  
* CTL-VERSION, CTL-QA.

**Entradas:** requerimientos, usuarios, procesos, casos de uso.

**Salidas:** wireframes, flujos, prototipos, recomendaciones UX.

**Valor:** hace que el ERP sea usable y no solo funcional.

---

### **A51. Agente Frontend y Componentes**

**Misión:** construir y estructurar interfaces del sistema.

**Habilidades funcionales:**

* Frontend.  
* Componentes.  
* Formularios.  
* Tablas.  
* Pantallas.  
* Validaciones visuales.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-API.  
* PR-VAL, PR-QA, PR-COMP.  
* OUT-DOC, OUT-CHK, OUT-BIT.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** diseño UI, requerimientos, APIs, datos, reglas.

**Salidas:** pantallas, componentes, formularios, interfaz funcional.

**Valor:** convierte procesos en herramientas visuales para usuarios.

---

### **A52. Agente Design System y QA Visual**

**Misión:** mantener consistencia visual y calidad de experiencia.

**Habilidades funcionales:**

* Design system.  
* Consistencia visual.  
* Tokens.  
* Patrones UI.  
* Revisión de experiencia.  
* QA visual.

**Habilidades técnicas:**

* IN-IMG, IN-DOCS, IN-TXT.  
* PR-VAL, PR-QA, PR-COMP.  
* OUT-CHK, OUT-DOC, OUT-REC.  
* CTL-REJECT, CTL-VERSION.

**Entradas:** pantallas, prototipos, componentes, lineamientos de marca.

**Salidas:** revisión visual, design system, correcciones UI, estándares.

**Valor:** evita que el sistema se vea improvisado o inconsistente.

---

## **Equipo 5.3 — Backend, Base de Datos e Integraciones**

### **A53. Agente Backend y Lógica de Negocio**

**Misión:** diseñar lógica interna, servicios y procesos transaccionales.

**Habilidades funcionales:**

* Backend.  
* Servicios.  
* Reglas de negocio.  
* Validaciones.  
* Procesos transaccionales.  
* Manejo de errores.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-API, IN-DB.  
* PR-CLASS, PR-VAL, PR-QA, PR-TRACE.  
* OUT-DOC, OUT-CHK, OUT-BIT.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** requerimientos, datos, reglas, flujos, integraciones.

**Salidas:** servicios backend, lógica de negocio, validaciones, documentación técnica.

**Valor:** sostiene la operación real del ERP.

---

### **A54. Agente Database, SQL y Modelo de Datos**

**Misión:** diseñar estructura de datos robusta y escalable.

**Habilidades funcionales:**

* Tablas.  
* Relaciones.  
* SQL.  
* Migraciones.  
* Integridad.  
* Diccionario de datos.  
* Performance de consultas.

**Habilidades técnicas:**

* IN-DB, IN-CSV, IN-XLSX, IN-ERP.  
* PR-CLASS, PR-VAL, PR-COMP, PR-QA.  
* OUT-DOC, OUT-TABLE, OUT-CHK.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** entidades, procesos, requerimientos, reportes, datos.

**Salidas:** modelo de datos, tablas, relaciones, queries, diccionario de datos.

**Valor:** evita que el ERP crezca sobre una base de datos mal diseñada.

---

### **A55. Agente APIs, Integraciones y Automatización Técnica**

**Misión:** conectar sistemas internos y externos.

**Habilidades funcionales:**

* APIs.  
* Webhooks.  
* Integraciones.  
* Servicios externos.  
* Automatización técnica.  
* Interoperabilidad.

**Habilidades técnicas:**

* IN-API, IN-DB, IN-ERP, IN-DOCS.  
* PR-VAL, PR-COMP, PR-TRACE, PR-QA.  
* OUT-DOC, OUT-CHK, OUT-BIT.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** sistemas, APIs, requerimientos, eventos, datos externos.

**Salidas:** endpoints, integraciones, documentación API, flujos automatizados.

**Valor:** permite que la oficina virtual se conecte con herramientas reales.

---

### **A56. Agente Seguridad, Permisos y Performance Técnico**

**Misión:** proteger el sistema y asegurar rendimiento técnico.

**Habilidades funcionales:**

* Roles.  
* Permisos.  
* Autenticación.  
* Auditoría de accesos.  
* Performance.  
* Buenas prácticas.  
* Seguridad técnica.

**Habilidades técnicas:**

* IN-DB, IN-ERP, IN-DASH, IN-DOCS.  
* PR-VAL, PR-RISK, PR-ANOM, PR-QA.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-AUDIT, CTL-ESC, CTL-LIMIT.

**Entradas:** usuarios, roles, módulos, logs, arquitectura, flujos.

**Salidas:** matriz de permisos, recomendaciones de seguridad, alertas técnicas, optimizaciones.

**Valor:** protege datos, accesos y estabilidad del sistema.

---

## **Equipo 5.4 — QA, DevOps y Documentación Técnica**

### **A57. Agente QA Técnico y Testing**

**Misión:** evitar errores técnicos y funcionales antes de liberar cambios.

**Habilidades funcionales:**

* Test cases.  
* Testing funcional.  
* Testing técnico.  
* Regression.  
* Bugs.  
* Validación de release.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-API, IN-DB.  
* PR-VAL, PR-QA, PR-ANOM, PR-TRACE.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-BIT.  
* CTL-REJECT, CTL-AUDIT, CTL-VERSION.

**Entradas:** módulos, requerimientos, código, criterios de aceptación.

**Salidas:** casos de prueba, reporte de bugs, validación QA, checklist de release.

**Valor:** evita que errores lleguen a producción.

---

### **A58. Agente DevOps, Release y Ambientes**

**Misión:** administrar despliegues, versiones y ambientes.

**Habilidades funcionales:**

* Deployments.  
* CI/CD.  
* Ambientes.  
* Versiones.  
* Release checklist.  
* Rollbacks.

**Habilidades técnicas:**

* IN-DOCS, IN-API, IN-DB, IN-DASH.  
* PR-VAL, PR-TRACE, PR-QA, PR-RISK.  
* OUT-BIT, OUT-CHK, OUT-REP, OUT-ALERT.  
* CTL-VERSION, CTL-AUDIT, CTL-ESC.

**Entradas:** código, versión, checklist, ambientes, aprobación QA.

**Salidas:** release, despliegue, control de versión, reporte de deployment.

**Valor:** permite publicar cambios sin romper el sistema.

---

### **A59. Agente Monitoreo, Logs y Continuidad**

**Misión:** vigilar estabilidad técnica y continuidad del sistema.

**Habilidades funcionales:**

* Logs.  
* Monitoreo.  
* Alertas técnicas.  
* Backups.  
* Disponibilidad.  
* Continuidad.

**Habilidades técnicas:**

* IN-DASH, IN-DB, IN-API, IN-CSV.  
* PR-ANOM, PR-RISK, PR-VAL, PR-TRACE.  
* OUT-ALERT, OUT-REP, OUT-DASH, OUT-BIT.  
* CTL-ESC, CTL-AUDIT.

**Entradas:** logs, métricas, backups, errores, servicios.

**Salidas:** reporte de monitoreo, alertas, estado de sistema, plan de continuidad.

**Valor:** detecta fallas antes de que afecten operación.

---

### **A60. Agente Documentación Técnica**

**Misión:** documentar arquitectura, decisiones técnicas y operación del sistema.

**Habilidades funcionales:**

* Documentación técnica.  
* Arquitectura.  
* Changelog.  
* Manuales técnicos.  
* Onboarding.  
* Decisiones técnicas.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-PDF, IN-API, IN-DB.  
* PR-SUM, PR-CLASS, PR-TRACE, PR-VAL.  
* OUT-DOC, OUT-BIT, OUT-CHK, OUT-PACK.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** arquitectura, código, releases, decisiones, APIs, modelos de datos.

**Salidas:** documentación técnica, changelog, diagramas, guías de onboarding.

**Valor:** evita dependencia de una sola persona técnica.

---

## **Equipo 5.5 — Data, BI e Inteligencia Artificial**

### **A61. Agente Data Analyst / BI**

**Misión:** convertir datos en insights accionables.

**Habilidades funcionales:**

* Análisis de datos.  
* Limpieza conceptual.  
* KPIs.  
* Tendencias.  
* Anomalías.  
* Insights.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-DB, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SUM.  
* OUT-REP, OUT-TABLE, OUT-REC, OUT-ALERT.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** ERP, operaciones, finanzas, comercial, talento, calidad.

**Salidas:** análisis BI, insights, anomalías, recomendaciones.

**Valor:** convierte datos dispersos en inteligencia de negocio.

---

### **A62. Agente Dashboards y Reporting**

**Misión:** crear tableros y reportes automatizados.

**Habilidades funcionales:**

* Dashboards.  
* Reportes.  
* Scorecards.  
* Métricas.  
* Visualización.  
* Automatización de reportes.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-DB, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-VAL, PR-QA.  
* OUT-DASH, OUT-REP, OUT-TABLE, OUT-BRIEF.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** KPIs, datos ERP, requerimientos de dirección, métricas.

**Salidas:** dashboards, scorecards, reportes automáticos, visualizaciones.

**Valor:** da visibilidad permanente a la empresa.

---

### **A63. Agente Automatización y Workflows**

**Misión:** automatizar procesos repetitivos y conectar flujos.

**Habilidades funcionales:**

* Workflows.  
* Triggers.  
* Automatizaciones.  
* Integraciones operativas.  
* Alertas.  
* Procesos automáticos.

**Habilidades técnicas:**

* IN-API, IN-ERP, IN-DB, IN-DASH, IN-EMAIL.  
* PR-CLASS, PR-VAL, PR-TRACE, PR-QA.  
* OUT-DOC, OUT-BIT, OUT-CHK, OUT-ALERT.  
* CTL-VERSION, CTL-AUDIT, CTL-ESC.

**Entradas:** procesos, eventos, sistemas, reglas, tareas repetitivas.

**Salidas:** workflows, automatizaciones, triggers, documentación de flujo.

**Valor:** reduce trabajo manual y acelera operación.

---

### **A64. Agente Arquitecto de Agentes IA**

**Misión:** diseñar estructura, roles y capacidades de agentes IA.

**Habilidades funcionales:**

* Diseño de agentes.  
* Roles.  
* Herramientas.  
* Memoria.  
* Límites.  
* Arquitectura multiagente.  
* Diseño de orquestación.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-ERP, IN-DASH.  
* PR-CLASS, PR-COMP, PR-QA, PR-TRACE.  
* OUT-DOC, OUT-CHK, OUT-REC, OUT-BIT.  
* CTL-LIMIT, CTL-VERSION, CTL-AUDIT.

**Entradas:** procesos, necesidades de áreas, errores, nuevas funciones.

**Salidas:** diseño de agentes, prompts estructurales, arquitectura multiagente, matriz de roles.

**Valor:** permite que la oficina virtual evolucione sin volverse caótica.

---

### **A65. Agente Prompts y Evaluación IA**

**Misión:** mejorar instrucciones, prompts y desempeño de agentes.

**Habilidades funcionales:**

* Prompts maestros.  
* Evaluación.  
* Criterios de calidad.  
* Pruebas de agentes.  
* Mejora de instrucciones.  
* Detección de errores.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-PDF, IN-ERP.  
* PR-QA, PR-TRACE, PR-VAL, PR-COMP.  
* OUT-DOC, OUT-REP, OUT-SCORE, OUT-REC.  
* CTL-CONF, CTL-REJECT, CTL-VERSION.

**Entradas:** entregables de agentes, errores, criterios, feedback humano.

**Salidas:** prompts mejorados, evaluación IA, reporte de desempeño, criterios de calidad.

**Valor:** mejora calidad de la oficina completa.

---

## **Equipo 5.6 — IT, Ciberseguridad y Soporte Interno**

### **A66. Agente IT Admin y Soporte Interno**

**Misión:** administrar herramientas, usuarios y soporte tecnológico interno.

**Habilidades funcionales:**

* Usuarios.  
* Correos.  
* Herramientas.  
* Tickets internos.  
* Soporte.  
* Inventario tecnológico.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-DOCS, IN-ERP.  
* PR-CLASS, PR-VAL, PR-PRIOR, PR-SUM.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-BIT.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** usuarios, solicitudes, equipos, herramientas, tickets.

**Salidas:** ticket resuelto, usuario configurado, inventario, reporte soporte.

**Valor:** mantiene funcionando la infraestructura diaria.

---

### **A67. Agente Accesos, Permisos y Seguridad Digital**

**Misión:** controlar permisos, accesos y seguridad de cuentas.

**Habilidades funcionales:**

* Accesos.  
* Roles.  
* Permisos.  
* Contraseñas.  
* Seguridad de cuentas.  
* Auditoría de accesos.

**Habilidades técnicas:**

* IN-DOCS, IN-ERP, IN-DB, IN-DASH.  
* PR-VAL, PR-RISK, PR-ANOM, PR-QA.  
* OUT-CHK, OUT-ALERT, OUT-REP, OUT-REC.  
* CTL-LIMIT, CTL-AUDIT, CTL-ESC.

**Entradas:** usuarios, roles, sistemas, políticas, logs.

**Salidas:** matriz de permisos, alertas de acceso, recomendaciones de seguridad.

**Valor:** reduce riesgo de filtraciones o accesos indebidos.

---

### **A68. Agente Backups, Continuidad e Incidentes TI**

**Misión:** proteger continuidad operativa ante fallas tecnológicas.

**Habilidades funcionales:**

* Backups.  
* Continuidad.  
* Recuperación.  
* Incidentes.  
* Disponibilidad.  
* Plan de contingencia.

**Habilidades técnicas:**

* IN-DASH, IN-DB, IN-DOCS, IN-ERP.  
* PR-RISK, PR-VAL, PR-ANOM, PR-TRACE.  
* OUT-REP, OUT-ALERT, OUT-CHK, OUT-BIT.  
* CTL-ESC, CTL-AUDIT, CTL-HITL.

**Entradas:** sistemas, backups, logs, incidentes, criticidad.

**Salidas:** reporte de backup, plan de recuperación, estado de continuidad, incidente cerrado.

**Valor:** protege la operación digital frente a caídas o pérdida de datos.

---

# **13\. Departamento 06: Legal, Compliance y Riesgos**

## **Propósito**

Proteger jurídicamente a la empresa, controlar cumplimiento, gestionar riesgos, seguros, siniestros y auditorías.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 6.1 Legal Corporativo y Contratos | 3 |
| 6.2 Compliance, Permisos y Regulación de Transporte | 3 |
| 6.3 Riesgos, Seguros y Siniestros | 3 |
| 6.4 Auditoría Interna y Control | 4 |

---

## **Equipo 6.1 — Legal Corporativo y Contratos**

### **A69. Agente Legal Corporativo**

**Misión:** mantener estructura societaria y gobierno legal ordenados.

**Habilidades funcionales:**

* Actas.  
* Poderes.  
* Asambleas.  
* Gobierno legal.  
* Estructura societaria.  
* Expediente corporativo.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-TXT, IN-EMAIL.  
* PR-EXT, PR-VAL, PR-TRACE, PR-RISK.  
* OUT-DOC, OUT-CHK, OUT-PACK, OUT-ALERT.  
* CTL-HITL, CTL-AUDIT, CTL-CONF.

**Entradas:** actas, estatutos, poderes, decisiones, documentos notariales.

**Salidas:** expediente legal, resumen societario, checklist de acuerdos, alertas.

**Valor:** mantiene ordenada la base legal de la empresa.

---

### **A70. Agente Contratos y Obligaciones**

**Misión:** revisar contratos y controlar obligaciones contractuales.

**Habilidades funcionales:**

* Contratos.  
* Obligaciones.  
* Vencimientos.  
* Versiones.  
* Checklist de firma.  
* Seguimiento contractual.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-TXT, IN-EMAIL.  
* PR-EXT, PR-COMP, PR-VAL, PR-TRACE.  
* OUT-DOC, OUT-CHK, OUT-TABLE, OUT-ALERT.  
* CTL-HITL, CTL-VERSION, CTL-AUDIT.

**Entradas:** contratos, anexos, propuestas, acuerdos, versiones.

**Salidas:** resumen contractual, matriz de obligaciones, vencimientos, checklist de firma.

**Valor:** evita incumplimientos por obligaciones olvidadas.

---

### **A71. Agente Riesgo Contractual y Cláusulas Críticas**

**Misión:** detectar riesgos en cláusulas contractuales.

**Habilidades funcionales:**

* Cláusulas críticas.  
* Penalizaciones.  
* Responsabilidades.  
* Riesgos.  
* Comparación contractual.  
* Alertas legales.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-TXT.  
* PR-EXT, PR-COMP, PR-RISK, PR-VAL.  
* OUT-REP, OUT-ALERT, OUT-REC, OUT-CHK.  
* CTL-HITL, CTL-CONF, CTL-ESC.

**Entradas:** contratos, anexos, condiciones comerciales, obligaciones.

**Salidas:** reporte de riesgos contractuales, cláusulas críticas, recomendaciones.

**Valor:** protege a la empresa antes de firmar compromisos riesgosos.

---

## **Equipo 6.2 — Compliance, Permisos y Regulación de Transporte**

### **A72. Agente Compliance Transporte**

**Misión:** asegurar cumplimiento operativo-regulatorio en transporte.

**Habilidades funcionales:**

* Cumplimiento transporte.  
* Checklists regulatorios.  
* Normativa aplicable.  
* Obligaciones.  
* Auditoría de cumplimiento.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-ERP, IN-TXT.  
* PR-VAL, PR-RISK, PR-TRACE, PR-QA.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** operación, permisos, regulación, documentos de unidad, documentos de viaje.

**Salidas:** checklist de cumplimiento, alertas regulatorias, reporte compliance.

**Valor:** reduce riesgo de multas, bloqueos operativos o incumplimientos.

---

### **A73. Agente Permisos y Expedientes Regulatorios**

**Misión:** controlar permisos, expedientes y vencimientos regulatorios.

**Habilidades funcionales:**

* Permisos.  
* Expedientes por unidad.  
* Expedientes por operador.  
* Vigencias.  
* Renovaciones.  
* Alertas de vencimiento.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-XLSX, IN-ERP.  
* PR-CLASS, PR-VAL, PR-TRACE, PR-PRIOR.  
* OUT-PACK, OUT-CHK, OUT-ALERT, OUT-TABLE.  
* CTL-AUDIT, CTL-ESC.

**Entradas:** permisos, documentos de unidad, operador, seguros, verificaciones.

**Salidas:** expediente regulatorio, alertas de vencimiento, checklist de renovación.

**Valor:** evita operar con documentos vencidos o incompletos.

---

### **A74. Agente Carta Porte y CFDI Logístico**

**Misión:** validar consistencia fiscal-operativa de Carta Porte y CFDI logístico.

**Habilidades funcionales:**

* Carta Porte.  
* CFDI.  
* Datos logísticos.  
* Requisitos documentales.  
* Inconsistencias.  
* Validación fiscal-operativa.

**Habilidades técnicas:**

* IN-PDF, IN-XLSX, IN-ERP, IN-DOCS.  
* PR-EXT, PR-VAL, PR-COMP, PR-QA.  
* OUT-CHK, OUT-ALERT, OUT-REP.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** cliente, origen, destino, mercancía, unidad, operador, CFDI.

**Salidas:** validación Carta Porte, inconsistencias, checklist fiscal-operativo.

**Valor:** reduce errores en documentos críticos para transporte y facturación.

---

## **Equipo 6.3 — Riesgos, Seguros y Siniestros**

### **A75. Agente Riesgos Empresariales y Mitigación**

**Misión:** identificar, medir y mitigar riesgos empresariales.

**Habilidades funcionales:**

* Matriz de riesgos.  
* Riesgo operativo.  
* Riesgo financiero.  
* Riesgo legal.  
* Riesgo reputacional.  
* Plan de mitigación.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DASH, IN-ERP.  
* PR-RISK, PR-COMP, PR-SIM, PR-PRIOR.  
* OUT-REP, OUT-TABLE, OUT-ALERT, OUT-REC.  
* CTL-HITL, CTL-ESC.

**Entradas:** operaciones, finanzas, legal, clientes, incidentes, auditorías.

**Salidas:** matriz de riesgos, planes de mitigación, semáforo de riesgo.

**Valor:** permite anticipar problemas antes de que se materialicen.

---

### **A76. Agente Seguros y Coberturas**

**Misión:** controlar pólizas, coberturas y renovaciones.

**Habilidades funcionales:**

* Pólizas.  
* Coberturas.  
* Renovaciones.  
* Exclusiones.  
* Comparativos.  
* Vigencias.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-XLSX, IN-EMAIL.  
* PR-EXT, PR-COMP, PR-VAL, PR-RISK.  
* OUT-REP, OUT-TABLE, OUT-ALERT, OUT-CHK.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** pólizas, unidades, mercancía, siniestros, contratos.

**Salidas:** reporte de coberturas, alertas de renovación, riesgos de cobertura.

**Valor:** evita huecos de cobertura ante eventos graves.

---

### **A77. Agente Siniestros y Reclamaciones**

**Misión:** gestionar expedientes de siniestros y reclamaciones.

**Habilidades funcionales:**

* Expediente de siniestro.  
* Reclamaciones.  
* Seguimiento.  
* Recuperación.  
* Evidencias.  
* Cierre.

**Habilidades técnicas:**

* IN-PDF, IN-IMG, IN-DOCS, IN-EMAIL, IN-GPS.  
* PR-EXT, PR-CLASS, PR-TRACE, PR-RISK.  
* OUT-PACK, OUT-REP, OUT-BIT, OUT-ALERT.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** incidente, fotos, póliza, reporte, facturas, documentos.

**Salidas:** expediente de siniestro, reclamación preparada, seguimiento, cierre.

**Valor:** mejora recuperación económica y trazabilidad ante incidentes.

---

## **Equipo 6.4 — Auditoría Interna y Control**

### **A78. Agente Auditor Operativo**

**Misión:** auditar viajes, combustible, evidencias, mantenimiento y tráfico.

**Habilidades funcionales:**

* Auditoría operativa.  
* Revisión de viajes.  
* Combustible.  
* Evidencias.  
* Desviaciones.  
* Controles operativos.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-GPS, IN-IMG.  
* PR-ANOM, PR-VAL, PR-QA, PR-TRACE.  
* OUT-REP, OUT-ALERT, OUT-CHK, OUT-REC.  
* CTL-AUDIT, CTL-REJECT.

**Entradas:** viajes, bitácoras, combustible, evidencias, GPS, mantenimiento.

**Salidas:** hallazgos operativos, reporte de auditoría, acciones correctivas.

**Valor:** detecta fugas operativas y desviaciones de proceso.

---

### **A79. Agente Auditor Financiero**

**Misión:** auditar pagos, cobros, facturas, costos y presupuestos.

**Habilidades funcionales:**

* Auditoría financiera.  
* CXC.  
* CXP.  
* Facturas.  
* Costos.  
* Desviaciones.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-PDF, IN-ERP, IN-DASH.  
* PR-CALC, PR-VAL, PR-ANOM, PR-TRACE.  
* OUT-REP, OUT-TABLE, OUT-ALERT, OUT-REC.  
* CTL-AUDIT, CTL-REJECT.

**Entradas:** bancos, facturas, pagos, cobros, reportes financieros.

**Salidas:** hallazgos financieros, alertas, recomendaciones de control.

**Valor:** protege dinero y reduce errores financieros.

---

### **A80. Agente Auditor Documental y Compliance**

**Misión:** auditar documentos, contratos, permisos, CFDI y Carta Porte.

**Habilidades funcionales:**

* Auditoría documental.  
* Compliance.  
* Expedientes.  
* Contratos.  
* Permisos.  
* CFDI.  
* Carta Porte.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-XLSX, IN-ERP.  
* PR-EXT, PR-VAL, PR-QA, PR-TRACE.  
* OUT-REP, OUT-CHK, OUT-ALERT, OUT-PACK.  
* CTL-AUDIT, CTL-REJECT.

**Entradas:** expedientes, permisos, contratos, CFDI, Carta Porte.

**Salidas:** reporte documental, hallazgos compliance, documentos faltantes.

**Valor:** evita que la empresa falle por documentación incompleta.

---

### **A81. Agente Control Interno y Hallazgos**

**Misión:** consolidar controles, hallazgos y acciones correctivas.

**Habilidades funcionales:**

* Controles internos.  
* Hallazgos.  
* Acciones correctivas.  
* Seguimiento.  
* Cierre.  
* Matriz de control.

**Habilidades técnicas:**

* IN-XLSX, IN-ERP, IN-DASH, IN-DOCS.  
* PR-CLASS, PR-PRIOR, PR-TRACE, PR-QA.  
* OUT-TABLE, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-AUDIT, CTL-VERSION.

**Entradas:** auditorías, hallazgos, procesos, riesgos, responsables.

**Salidas:** matriz de hallazgos, controles, acciones correctivas, cierre de auditoría.

**Valor:** convierte auditorías en mejoras concretas.

---

# **14\. Departamento 07: Talento y Cultura**

## **Propósito**

Atraer talento, organizar expedientes, apoyar nómina, desarrollar capacidades, construir cultura y medir desempeño.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 7.1 Reclutamiento, Onboarding y Expedientes | 3 |
| 7.2 Nómina, Compensaciones e Incidencias | 3 |
| 7.3 Capacitación, Cultura y Desempeño | 3 |

---

## **Equipo 7.1 — Reclutamiento, Onboarding y Expedientes**

### **A82. Agente Perfiles, Reclutamiento y Scoring**

**Misión:** estructurar perfiles de puesto y filtrar candidatos.

**Habilidades funcionales:**

* Perfil de puesto.  
* Vacante.  
* Screening.  
* Scoring.  
* Guía de entrevista.  
* Ranking de candidatos.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-EMAIL.  
* PR-CLASS, PR-SUM, PR-SCORE, PR-VAL.  
* OUT-DOC, OUT-SCORE, OUT-CHK, OUT-REP.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** necesidad de puesto, CVs, criterios, competencias, cultura.

**Salidas:** perfil de puesto, ranking de candidatos, guía de entrevista, score.

**Valor:** permite contratar con criterios claros y no por intuición.

---

### **A83. Agente Onboarding y Expedientes Laborales**

**Misión:** organizar ingreso y documentación del colaborador.

**Habilidades funcionales:**

* Onboarding.  
* Checklist de ingreso.  
* Expediente laboral.  
* Contratos laborales.  
* Documentos.  
* Alta interna.

**Habilidades técnicas:**

* IN-PDF, IN-DOCS, IN-EMAIL, IN-XLSX.  
* PR-CLASS, PR-EXT, PR-VAL, PR-TRACE.  
* OUT-PACK, OUT-CHK, OUT-DOC, OUT-ALERT.  
* CTL-AUDIT, CTL-VERSION.

**Entradas:** candidato seleccionado, documentos, contrato, puesto, área.

**Salidas:** expediente completo, checklist de onboarding, documentos pendientes.

**Valor:** profesionaliza el ingreso de personas desde el inicio.

---

### **A84. Agente Experiencia del Colaborador**

**Misión:** mejorar integración y retención temprana.

**Habilidades funcionales:**

* Seguimiento 30/60/90 días.  
* Feedback.  
* Integración.  
* Riesgo de rotación.  
* Mejora de onboarding.  
* Experiencia interna.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-XLSX, IN-DASH.  
* PR-SUM, PR-RISK, PR-SCORE, PR-ANOM.  
* OUT-REP, OUT-ALERT, OUT-REC, OUT-SCORE.  
* CTL-ESC, CTL-CONF.

**Entradas:** feedback, desempeño inicial, jefe directo, encuestas, onboarding.

**Salidas:** reporte 30/60/90, alertas de rotación, recomendaciones.

**Valor:** ayuda a retener talento y corregir problemas de integración temprano.

---

## **Equipo 7.2 — Nómina, Compensaciones e Incidencias**

### **A85. Agente Pre-Nómina e Incidencias**

**Misión:** preparar información previa de nómina e incidencias.

**Habilidades funcionales:**

* Incidencias.  
* Asistencia.  
* Variables.  
* Pre-nómina.  
* Validaciones.  
* Paquete para contador.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-DOCS, IN-ERP.  
* PR-CALC, PR-VAL, PR-CLASS, PR-TRACE.  
* OUT-PACK, OUT-TABLE, OUT-CHK, OUT-ALERT.  
* CTL-HITL, CTL-AUDIT.

**Entradas:** asistencia, incidencias, bonos, horas, viajes, variables.

**Salidas:** pre-nómina, incidencias validadas, paquete para contador.

**Valor:** reduce errores de pago y carga administrativa.

---

### **A86. Agente Compensaciones y Bonos**

**Misión:** diseñar y analizar esquemas de pago e incentivos.

**Habilidades funcionales:**

* Bonos.  
* Variables.  
* Esquemas de pago.  
* Comparativos.  
* Incentivos por desempeño.  
* Operadores por viaje.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-SIM, PR-VAL.  
* OUT-TABLE, OUT-REP, OUT-REC.  
* CTL-HITL, CTL-CONF.

**Entradas:** desempeño, viajes, ventas, productividad, políticas.

**Salidas:** cálculo de bonos, propuesta de incentivos, análisis de compensación.

**Valor:** alinea pago con productividad y rentabilidad.

---

### **A87. Agente QA Laboral y Nómina**

**Misión:** revisar errores antes de procesar pagos laborales.

**Habilidades funcionales:**

* Validación de incidencias.  
* Validación de montos.  
* Consistencia de pagos.  
* Alertas de errores.  
* Revisión de variables.  
* Checklist laboral.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-DOCS, IN-ERP.  
* PR-VAL, PR-QA, PR-ANOM, PR-TRACE.  
* OUT-CHK, OUT-REP, OUT-ALERT.  
* CTL-REJECT, CTL-HITL, CTL-AUDIT.

**Entradas:** pre-nómina, incidencias, bonos, contratos, políticas.

**Salidas:** reporte QA nómina, errores, correcciones, aprobación preliminar.

**Valor:** evita pagos incorrectos y conflictos laborales.

---

## **Equipo 7.3 — Capacitación, Cultura y Desempeño**

### **A88. Agente Capacitación y Manuales Internos**

**Misión:** crear materiales de formación y manuales internos.

**Habilidades funcionales:**

* Cursos.  
* Manuales.  
* Inducción.  
* Evaluaciones de aprendizaje.  
* Matriz de competencias.  
* Certificación interna.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-IMG.  
* PR-SUM, PR-CLASS, PR-VAL, PR-QA.  
* OUT-DOC, OUT-CHK, OUT-REP.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** procesos, roles, necesidades, errores frecuentes, SOPs.

**Salidas:** manuales, cursos, evaluaciones, matriz de competencias.

**Valor:** permite formar personas con estándares claros.

---

### **A89. Agente Cultura, Comunicación y Clima**

**Misión:** fortalecer cultura organizacional y comunicación interna.

**Habilidades funcionales:**

* Valores.  
* Comunicados.  
* Encuestas de clima.  
* Feedback.  
* Reconocimiento.  
* Identidad cultural.

**Habilidades técnicas:**

* IN-TXT, IN-EMAIL, IN-XLSX, IN-DASH.  
* PR-SUM, PR-SCORE, PR-ANOM, PR-CLASS.  
* OUT-EMAIL, OUT-REP, OUT-SCORE, OUT-REC.  
* CTL-CONF, CTL-ESC.

**Entradas:** eventos internos, encuestas, feedback, valores, liderazgo.

**Salidas:** comunicados, reporte de clima, recomendaciones culturales.

**Valor:** construye identidad empresarial y reduce desgaste humano.

---

### **A90. Agente Desempeño y Desarrollo**

**Misión:** medir desempeño y apoyar crecimiento del equipo humano.

**Habilidades funcionales:**

* Evaluación.  
* Objetivos.  
* Planes de mejora.  
* Desarrollo.  
* Retroalimentación.  
* Seguimiento.

**Habilidades técnicas:**

* IN-XLSX, IN-DASH, IN-DOCS, IN-EMAIL.  
* PR-CALC, PR-SCORE, PR-COMP, PR-SUM.  
* OUT-REP, OUT-SCORE, OUT-REC, OUT-CHK.  
* CTL-HITL, CTL-CONF.

**Entradas:** KPIs, feedback, objetivos, rol, desempeño.

**Salidas:** evaluación de desempeño, plan de mejora, plan de desarrollo.

**Valor:** convierte desempeño en mejora continua, no solo evaluación.

---

# **15\. Departamento 08: Calidad, Procesos y Sostenibilidad**

## **Propósito**

Asegurar que la oficina opere con procesos claros, calidad, mejora continua, sostenibilidad, seguridad e higiene y auditoría de agentes IA.

## **Equipos**

| Equipo | Agentes |
| :---- | :---- |
| 8.1 Calidad, SOPs y Mejora Continua | 3 |
| 8.2 ESG, Seguridad e Higiene | 3 |
| 8.3 Auditoría y Calidad de Agentes IA | 3 |

---

## **Equipo 8.1 — Calidad, SOPs y Mejora Continua**

### **A91. Agente Procesos, SOPs y Control Documental**

**Misión:** documentar procesos y mantener control de versiones.

**Habilidades funcionales:**

* Mapeo de procesos.  
* SOPs.  
* Manuales.  
* Diagramas.  
* Versionamiento.  
* Control documental.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-ERP.  
* PR-CLASS, PR-SUM, PR-TRACE, PR-QA.  
* OUT-DOC, OUT-CHK, OUT-BIT, OUT-PACK.  
* CTL-VERSION, CTL-AUDIT.

**Entradas:** procesos reales, entrevistas, políticas, flujos, errores.

**Salidas:** SOPs, diagramas, manuales, matriz de procesos, control de versiones.

**Valor:** permite escalar sin que cada persona trabaje a su manera.

---

### **A92. Agente Calidad Operativa y Estándares**

**Misión:** revisar que los servicios y entregables cumplan estándares.

**Habilidades funcionales:**

* Estándares.  
* No conformidades.  
* Checklist de calidad.  
* Errores operativos.  
* Calidad por departamento.  
* Revisión de servicio.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-DOCS, IN-ERP, IN-DASH.  
* PR-VAL, PR-QA, PR-ANOM, PR-TRACE.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-REC.  
* CTL-REJECT, CTL-AUDIT.

**Entradas:** entregables, procesos, KPIs, quejas, auditorías.

**Salidas:** reporte de calidad, no conformidades, recomendaciones, aprobación QA.

**Valor:** evita que la empresa produzca rápido pero mal.

---

### **A93. Agente Mejora Continua y Causa-Raíz**

**Misión:** convertir errores en mejoras estructurales.

**Habilidades funcionales:**

* Causa-raíz.  
* Acciones correctivas.  
* Lecciones aprendidas.  
* Reducción de errores.  
* Reducción de tiempos.  
* Eficiencia.  
* Mejora de procesos.

**Habilidades técnicas:**

* IN-XLSX, IN-ERP, IN-DASH, IN-DOCS.  
* PR-ROOT, PR-COMP, PR-ANOM, PR-PRIOR.  
* OUT-REP, OUT-REC, OUT-CHK, OUT-ALERT.  
* CTL-AUDIT, CTL-VERSION.

**Entradas:** errores, incidencias, quejas, auditorías, KPIs.

**Salidas:** análisis causa-raíz, acciones correctivas, proyectos de mejora, lecciones aprendidas.

**Valor:** hace que cada error mejore el sistema.

---

## **Equipo 8.2 — ESG, Seguridad e Higiene**

### **A94. Agente ESG y Reportes de Impacto**

**Misión:** estructurar sostenibilidad, impacto social y gobierno responsable.

**Habilidades funcionales:**

* ESG.  
* Reportes.  
* Indicadores sociales.  
* Gobierno.  
* Impacto.  
* Políticas sostenibles.

**Habilidades técnicas:**

* IN-XLSX, IN-PDF, IN-DOCS, IN-DASH.  
* PR-CALC, PR-SUM, PR-COMP, PR-VAL.  
* OUT-REP, OUT-DASH, OUT-DOC, OUT-REC.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** operaciones, consumo, seguridad, gobierno, talento, comunidad.

**Salidas:** reporte ESG, indicadores de impacto, políticas sostenibles.

**Valor:** prepara a la empresa para clientes grandes y estándares modernos.

---

### **A95. Agente Indicadores Ambientales y Eficiencia Energética**

**Misión:** medir impacto ambiental y eficiencia energética.

**Habilidades funcionales:**

* Emisiones.  
* Combustible.  
* Eficiencia energética.  
* Huella ambiental.  
* Recomendaciones ambientales.  
* Consumo por ruta.

**Habilidades técnicas:**

* IN-XLSX, IN-CSV, IN-ERP, IN-DASH.  
* PR-CALC, PR-COMP, PR-ANOM, PR-SIM.  
* OUT-REP, OUT-TABLE, OUT-DASH, OUT-REC.  
* CTL-CONF, CTL-AUDIT.

**Entradas:** combustible, km, unidades, rutas, mantenimiento.

**Salidas:** indicadores ambientales, reporte de emisiones, recomendaciones de eficiencia.

**Valor:** conecta ahorro operativo con sostenibilidad.

---

### **A96. Agente Seguridad e Higiene Laboral**

**Misión:** apoyar seguridad laboral y prevención de accidentes.

**Habilidades funcionales:**

* Protocolos.  
* EPP.  
* Accidentes laborales.  
* Capacitación.  
* Incidentes.  
* Checklists.  
* Prevención.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-DOCS, IN-IMG, IN-XLSX.  
* PR-CLASS, PR-RISK, PR-ROOT, PR-VAL.  
* OUT-CHK, OUT-REP, OUT-ALERT, OUT-DOC.  
* CTL-ESC, CTL-HITL, CTL-AUDIT.

**Entradas:** incidentes, roles, operación, capacitación, regulaciones internas.

**Salidas:** checklist de seguridad, reporte de incidentes, protocolo, acciones preventivas.

**Valor:** protege a las personas y reduce riesgos laborales.

---

## **Equipo 8.3 — Auditoría y Calidad de Agentes IA**

### **A97. Agente Evaluador de Agentes IA**

**Misión:** medir desempeño y confiabilidad de agentes IA.

**Habilidades funcionales:**

* Evaluaciones.  
* Score de agentes.  
* Pruebas.  
* Calidad de entregables.  
* Comparación contra criterios.  
* Benchmark interno.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DOCS, IN-ERP.  
* PR-QA, PR-COMP, PR-SCORE, PR-TRACE.  
* OUT-SCORE, OUT-REP, OUT-REC, OUT-ALERT.  
* CTL-CONF, CTL-AUDIT, CTL-REJECT.

**Entradas:** entregables de agentes, criterios, feedback humano, errores.

**Salidas:** score de agentes, reporte de evaluación, recomendaciones de mejora.

**Valor:** mide si los agentes realmente están aportando valor.

---

### **A98. Agente Trazabilidad, Errores y Alucinaciones**

**Misión:** detectar errores, inconsistencias y afirmaciones no verificadas.

**Habilidades funcionales:**

* Detección de alucinaciones.  
* Trazabilidad.  
* Consistencia.  
* Evidencia.  
* Validación de supuestos.  
* Registro de errores.  
* Verificación de fuentes.

**Habilidades técnicas:**

* IN-TXT, IN-PDF, IN-XLSX, IN-DOCS, IN-ERP, IN-DASH.  
* PR-VAL, PR-QA, PR-TRACE, PR-COMP, PR-ANOM.  
* OUT-REP, OUT-ALERT, OUT-REC, OUT-CHK.  
* CTL-CONF, CTL-REJECT, CTL-AUDIT.

**Entradas:** reportes de agentes, datos, fuentes, supuestos, documentos.

**Salidas:** reporte de errores, advertencias de trazabilidad, correcciones solicitadas.

**Valor:** evita que la IA produzca información convincente pero falsa.

---

### **A99. Agente Mejora de Prompts y Control IA**

**Misión:** mejorar prompts, instrucciones y diseño operativo de agentes.

**Habilidades funcionales:**

* Prompts maestros.  
* Instrucciones.  
* Mejora continua de agentes.  
* Plantillas.  
* Criterios de salida.  
* Rediseño de roles.  
* Control operativo IA.

**Habilidades técnicas:**

* IN-TXT, IN-DOCS, IN-PDF, IN-ERP.  
* PR-QA, PR-TRACE, PR-COMP, PR-SUM.  
* OUT-DOC, OUT-CHK, OUT-REC, OUT-BIT.  
* CTL-VERSION, CTL-AUDIT, CTL-REJECT.

**Entradas:** evaluaciones, errores, feedback, prompts actuales, procesos.

**Salidas:** prompts mejorados, plantillas, criterios de calidad, rediseño de agente.

**Valor:** mantiene viva y mejorando la arquitectura de IA.

---

# **16\. Reglas de autoridad y control**

## **16.1 Los agentes pueden**

* Analizar.  
* Preparar.  
* Documentar.  
* Recomendar.  
* Comparar.  
* Simular.  
* Revisar.  
* Alertar.  
* Organizar.  
* Generar borradores.  
* Detectar errores.  
* Preparar paquetes documentales.

## **16.2 Los agentes no deben autorizar solos**

* Pagos importantes.  
* Contratos.  
* Declaraciones fiscales.  
* Precios estratégicos.  
* Compra de unidades.  
* Contrataciones críticas.  
* Despidos.  
* Respuestas legales.  
* Cambios de estrategia.  
* Decisiones con riesgo alto.

## **16.3 Regla final de control**

Agente produce.  
QA revisa.  
Líder aprueba.  
Humano autoriza.  
Sistema registra.  
---

# **17\. Flujo operativo estándar**

Todo trabajo dentro de la oficina virtual debe seguir esta lógica:

Solicitud o necesidad  
↓  
Agente Orquestador General  
↓  
Agente Líder de Departamento  
↓  
Equipo correspondiente  
↓  
Agente líder operativo del equipo  
↓  
Agentes especialistas  
↓  
Agente QA o auditor cuando aplique  
↓  
Líder departamental  
↓  
Orquestador General  
↓  
Humano autoriza si es necesario  
↓  
Entrega final  
---

# **18\. Tipos de flujo**

## **Flujo independiente**

Un agente puede resolver sin activar a otros.

Agente Administración Documental  
↓  
Ordena expediente  
↓  
Entrega checklist

## **Flujo secuencial**

Un agente termina y pasa al siguiente.

Pricing  
↓  
Propuesta  
↓  
QA Comercial  
↓  
Líder Comercial

## **Flujo paralelo**

Varios departamentos trabajan al mismo tiempo.

Nuevo cliente grande  
↓  
Comercial \+ Finanzas \+ Operaciones \+ Legal \+ Riesgos  
↓  
Orquestador integra  
↓  
Humano decide

## **Flujo con corrección**

Agente produce  
↓  
QA revisa  
↓  
Si falla, regresa  
↓  
Si aprueba, continúa  
---

# **19\. Resumen final de agentes por departamento**

| Departamento | Líder departamental | Equipos | Agentes núcleo | Total con líder |
| :---- | :---- | :---- | :---- | :---- |
| Dirección y Gobierno | 1 | 2 | 5 | 6 |
| Finanzas, Contabilidad y Administración | 1 | 4 | 14 | 15 |
| Operaciones Logísticas | 1 | 5 | 16 | 17 |
| Comercial y Cliente | 1 | 4 | 11 | 12 |
| Tecnología, Datos e Innovación | 1 | 6 | 22 | 23 |
| Legal, Compliance y Riesgos | 1 | 4 | 13 | 14 |
| Talento y Cultura | 1 | 3 | 9 | 10 |
| Calidad, Procesos y Sostenibilidad | 1 | 3 | 9 | 10 |
| Orquestador General | 1 | — | — | 1 |
| **Total** | **9 incluyendo orquestador** | **31** | **99** | **108** |

---

# **20\. Conclusión**

La Oficina Virtual de Agentes IA queda compuesta por:

1 Agente Orquestador General  
8 Agentes Líderes de Departamento  
31 Equipos Digitales  
99 Agentes Núcleo  
108 Agentes Totales

La diferencia clave de esta versión integrada es que cada agente ya no se define únicamente por su función de negocio, sino también por:

* Qué información puede recibir.  
* Qué formatos puede interpretar.  
* Qué procesamiento puede hacer.  
* Qué entregables puede producir.  
* Qué límites tiene.  
* Cuándo debe escalar a humanos.  
* Cómo aporta valor al sistema completo.

Esta arquitectura permite construir una empresa digital completa, escalable, eficiente y controlada, con estructura de empresa global pero operable desde una base humana pequeña.

