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
.venv/Scripts/python -m services.cli --datos data/ejemplo    # costo por km y margen real
.venv/Scripts/python -m pytest                               # 63 pruebas
.venv/Scripts/python scripts/validate_registry.py --verbose  # §10.3
```

Detalle y requisito de salida hacia la Fase 1 en [docs/fase-0.md](docs/fase-0.md). La Fase 1 no
arranca hasta calibrar margen objetivo y mínimo por ruta con la distribución real que produce
`svc-profitability` ([umbrales.md](docs/umbrales.md)).

**La oficina virtual está abierta.** Doce puestos listos para construir el ERP: los nueve
consultores `C-01`…`C-09` más `D5-01` (Producto ERP) y `D5-03` (AgentOps), cada uno con nombre,
memoria persistente y **cero `ACT-*`** — no pueden tocar la operación, sólo producir texto y
código.

```bash
python -m office.cli estado      # quién está haciendo qué
python -m office.cli build       # regenera office/oficina.html
start office/oficina.html        # el plano en píxeles (macOS/Linux: open)
```

El plano no es una animación: quien teclea tiene un encargo `en_curso`, quien levanta la mano
espera una aprobación humana, y la silla vacía es un agente cuya fase no ha llegado. Detalle en
[docs/oficina-virtual.md](docs/oficina-virtual.md).
