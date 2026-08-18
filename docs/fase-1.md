# Fase 1 — Cotizar sin perder margen

**Cinco servicios determinísticos. Cero agentes encendidos.** Estado: las bases construidas.

La fase completa son cinco servicios más dos agentes (`D4-03` Pricing y `D2-03` Costos). Aquí
están los cinco servicios. **Los agentes no se encienden todavía**, y no por prudencia genérica:
les faltan dos condiciones de entrada que el §17.5 pone por escrito —margen objetivo y mínimo por
ruta calibrados, y la bandeja de HITL en producción.

| Servicio | Módulo | Contrato | Qué resuelve |
|---|---|---|---|
| `svc-runlog` | [services/runlog/](../services/runlog/) | [yaml](../registry/services/svc-runlog.yaml) | Por dónde pasó el caso y en qué va |
| `svc-trace` | [services/trace/](../services/trace/) | [yaml](../registry/services/svc-trace.yaml) | De dónde salió cada número |
| `svc-validation` | [services/validation/](../services/validation/) | [yaml](../registry/services/svc-validation.yaml) | Qué entregables no salen |
| `svc-budget` | [services/budget/](../services/budget/) | [yaml](../registry/services/svc-budget.yaml) | Cuánto puede gastar cada agente |
| `svc-pricing` | [services/pricing/](../services/pricing/) | [yaml](../registry/services/svc-pricing.yaml) | Precio, margen y quién autoriza |

```bash
python -m services.cli cotizar --ruta R-MTY-CDMX --unidad U-101 --cliente CL-01 \
    --operador OP-01 --diesel 26.59
```

Sale con código `1` si la cotización requiere un humano y `3` si el gate no la deja generarse.

## Por qué estos cinco y en este orden

`svc-runlog` primero porque **la trazabilidad no se retrofitea**. Si el primer agente arranca sin
registro, lo que se pierde no se recupera: no hay forma de saber después cuántas veces reintentó,
cuánto costó ni quién aprobó qué.

Los otros cuatro son las cuatro puertas por las que pasa un entregable antes de llegar a una
persona: **las reglas** (`svc-validation`), **las cifras** (`svc-trace`), **el costo del modelo**
(`svc-budget`) y **el precio** (`svc-pricing`).

## Lo que hace segura la Fase 1

### El gate de margen no se puede redactar mejor

El §4.1 lo dice de `D4-03`: "no calcula el precio. El gate de margen mínimo es determinístico: una
cotización bajo el umbral **no puede generarse**, no depende de que el LLM lo note".

Eso es literal en el código: `cotizar()` levanta `CotizacionBloqueada` antes de devolver nada.
La única forma de emitir por debajo del mínimo es una autorización de Dirección explícita, que
viaja escrita dentro de la cotización.

Quién autoriza sale de [`authority-gate.yaml`](../registry/policies/authority-gate.yaml), no del
criterio del momento:

| Situación | Autoriza |
|---|---|
| Tarifa de tabla y margen ≥ mínimo de la ruta | El agente, solo |
| Dentro de tabla pero con descuento ≤ 5% | Ana |
| Descuento > 5%, o fuera de tabla | Gabriel |
| Margen < mínimo de la ruta | **No se genera.** Gabriel puede autorizar la excepción |

El 5% no es un número inventado: sale del organigrama firmado ("aprobar descuentos mayores al
5%"). El margen mínimo sale de la tabla de precios que Gabriel ya mantiene por ruta.

### El número que suena mejor no llega al cliente

`svc-trace` guarda cada cifra con su servicio de origen y su consulta, y antes de entregar
reconcilia: cada cifra citada tiene que existir, coincidir al centavo, **y ningún número suelto
puede aparecer en la prosa sin respaldo**. Un agente que escribe "un margen cercano al 22.4%"
sobre un margen registrado de 18.30% no pasa la puerta.

### Un HITL vencido nunca se auto-aprueba

`svc-runlog` implementa la regla dura de §7.3 con calendario laboral real —lunes a viernes, 9 a
18, **en hora de Monterrey**, no en UTC—. Alta escala y luego bloquea; media escala una vez y
luego expira; baja expira como `no_atendido`. La función que resuelve un vencimiento no tiene un
caso "aprobar" y no puede tenerlo.

### Dos reintentos, no tres

El §12.3 permite dos. Al tercer rechazo de validación el caso se bloquea y lo mira una persona.
Sin ese tope, un agente que falla sistemáticamente al primer intento y acierta al segundo se ve
perfecto desde fuera mientras se degrada por dentro — por eso los reintentos se registran siempre.

## El flujo completo

```
O1 abre trace ─► svc-budget: ¿alcanza el presupuesto?
                 svc-pricing: precio, costo y margen  ──► svc-trace registra cada cifra
                 el agente redacta                    ──► svc-runlog registra tokens y costo
                 svc-validation: ¿cumple el contrato de §7.1?
                 svc-trace: ¿cuadra cada número con su origen?
                 gate ──► agente cierra │ Ana aprueba │ Gabriel aprueba │ no se genera
                 svc-runlog: entregado
```

Está probado de punta a punta en
[tests/integration/test_flujo_fase1.py](../tests/integration/test_flujo_fase1.py), incluido el
camino en que el gate bloquea y el caso queda esperando a Dirección.

## Lo que falta para encender `D4-03` y `D2-03`

| Condición (§17.5) | Estado |
|---|---|
| Margen objetivo y mínimo por ruta calibrados | **Pendiente.** El mínimo ya vive por ruta en la tabla de precios; el objetivo global sigue en `null`. Requiere el histórico real que produce la Fase 0 |
| Bandeja de HITL del ERP en producción, con los SLA de §7.3 | **Pendiente.** Es el primer hito del backlog del ERP (`E-001`). El cálculo del SLA ya existe; falta dónde llegue |
| `validate_registry.py` en verde | **Hecho.** 13 reglas en verde, 2 omitidas por depender del catálogo de habilidades |

Mientras tanto los cinco servicios son útiles sin ningún agente: `cotizar` desde la línea de
comandos ya aplica el gate completo y deja el rastro.

## Deudas declaradas

* **`svc-budget` no está calibrado.** Los topes salen del nivel de modelo de cada agente
  (§11.5), no de consumo observado, porque todavía no hay consumo que observar. Se recalibran con
  el primer mes real de `svc-runlog`.
* **El calendario laboral no conoce días festivos.** Es dato maestro y entra con el ERP. Hoy un
  SLA que cruza un festivo vence antes de lo debido.
* **La bitácora del `office/` no migró a `svc-runlog`.** Son dos registros por ahora: uno de la
  oficina de agentes (pausada) y otro de los casos. La migración es condición para reanudar los
  agentes — ver [oficina-virtual.md](oficina-virtual.md).
