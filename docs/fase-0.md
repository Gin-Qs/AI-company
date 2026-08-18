# Fase 0 — Fundación de datos

**Cuatro servicios. Cero agentes. Cero `ACT-*`.** Estado: construida.

Lo que entrega: **costo por km y margen real por viaje, ruta, cliente, unidad y operador**,
calculado con código determinístico y testeable. Ningún modelo participa; no hay nada que
alucinar.

| Servicio | Módulo | Contrato | Estado |
|---|---|---|---|
| `svc-masterdata` | [services/masterdata/](../services/masterdata/) | [svc-masterdata.yaml](../registry/services/svc-masterdata.yaml) | `built` |
| `svc-ingest` | [services/ingest/](../services/ingest/) | [svc-ingest.yaml](../registry/services/svc-ingest.yaml) | `built` |
| `svc-costing` | [services/costing/](../services/costing/) | [svc-costing.yaml](../registry/services/svc-costing.yaml) | `built` |
| `svc-profitability` | [services/profitability/](../services/profitability/) | [svc-profitability.yaml](../registry/services/svc-profitability.yaml) | `built` |

## Cómo se corre

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Linux/macOS: .venv/bin/python

.venv/Scripts/python -m services.cli --datos data/ejemplo
.venv/Scripts/python -m services.cli --datos data/real --json out/fase0.json
.venv/Scripts/python -m pytest
.venv/Scripts/python scripts/validate_registry.py --verbose
```

El CLI sale con código `1` si algún viaje quedó sin costear o alguna fila quedó en cuarentena:
una cifra incompleta no debe pasar por buena en un pipeline.

`data/ejemplo/` trae una operación ficticia de tres unidades y cuatro rutas para verificar la
instalación. **Los datos reales van en `data/real/`, que está en `.gitignore`.**

## Estructura de datos que espera

```
<datos>/catalogo/     clientes.csv  unidades.csv  operadores.csv  rutas.csv  tarifas.csv
                      parametros.yaml
<datos>/operacion/    viajes.csv  diesel.csv  gps.csv  banco.csv        (gps y banco opcionales)
```

Los encabezados se reconocen con alias: `Fecha Operación`, `F. Oper` y `fecha` son la misma
columna, y el BOM de Excel no molesta. Las cantidades aceptan `$ 1,234.50` y `(120)` para
negativos. Las fechas aceptan `2026-05-04`, `04/05/2026` y `04-05-2026`.

Columnas mínimas por archivo:

| Archivo | Columnas |
|---|---|
| `clientes.csv` | `cliente_id, nombre, rfc, dias_credito, activo` |
| `unidades.csv` | `unit_id, placa, tipo, modelo_anio, rendimiento_km_l, costo_adquisicion_mxn, valor_residual_mxn, vida_util_km, mantenimiento_mxn_km, costo_juego_llantas_mxn, vida_llantas_km, poliza_anual_mxn, km_anuales_esperados` |
| `operadores.csv` | `operador_id, nombre, esquema_pago (km\|fijo\|mixto), pago_mxn_km, sueldo_mensual_mxn, viaticos_mxn_dia, viajes_mensuales_esperados` |
| `rutas.csv` | `route_id, origen, destino, km, casetas_mxn, dias_estimados` |
| `tarifas.csv` | `tarifa_id, route_id, cliente_id, tipo_unidad, precio_mxn, margen_minimo_pct, vigencia_desde, vigencia_hasta, version, autorizado_por` |
| `viajes.csv` | `trip_id, route_id, unit_id, operador_id, cliente_id, fecha_inicio, fecha_fin, ingreso_facturado_mxn, estatus` |
| `diesel.csv` | `ticket_id, fecha, unit_id, litros, precio, importe, odometro_km, estacion` |
| `gps.csv` | `unit_id, trip_id, timestamp` + `km` **o** `lat`/`lon` |
| `banco.csv` | `fecha, concepto, cargo, abono, referencia, cuenta` (o una columna `monto` con signo) |

`tarifas.csv` **es la tabla de precios pre-aprobada de Gabriel**, cargada y versionada, no
sustituida (§17.2 y [umbrales.md](umbrales.md)). `cliente_id` y `tipo_unidad` vacíos significan
tarifa general; gana siempre la más específica y vigente.

## La fórmula de costeo

```
diesel        = km / rendimiento_km_l × precio_del_litro
casetas       = casetas de la ruta, o el importe real del viaje
operador      = según esquema: $/km × km + sueldo/viajes_esperados + viáticos × días
mantenimiento = mantenimiento_mxn_km × km
llantas       = (costo del juego / vida en km) × km
seguro        = (póliza anual / km anuales esperados) × km
depreciación  = ((adquisición − residual) / vida útil en km) × km
                                                        └─ costo variable
fijos         = costos fijos mensuales / (km o viajes mensuales de flota)
                                                        └─ + fijos = costo total
costo por km  = costo total / km
```

El precio del litro sale del **promedio ponderado por litros de los tickets del mes del viaje**,
no del precio de lista. El precio de referencia de `parametros.yaml` se usa solo si ese mes no
tiene tickets, y cuando eso pasa queda anotado como supuesto.

## Tres reglas duras

1. **Falta un dato, se detiene.** No hay defaults escondidos. Solo se deriva lo que el catálogo
   permite derivar por aritmética exacta, y cada derivación se reporta en `assumptions` (§7.1).
2. **Kilómetros no positivos bloquean el costeo.** Dividir entre cero produce un número que
   después alguien cotiza.
3. **Todo es `Decimal`.** Ningún `float` toca un peso.

En la ingesta la regla es distinta a propósito: **una fila mala se cuarentena con código de motivo
y el lote sigue**. Un estado de cuenta de 800 movimientos no puede perderse por un renglón de
comisiones sin referencia. Lo que no se puede derivar se rechaza; nada se descarta en silencio.

## Qué no hace esta fase

* No enciende ningún agente ni ejecuta ningún `ACT-*`. Por eso puede correr con los umbrales aún
  sin calibrar: ningún umbral gobierna nada todavía.
* No escribe en los sistemas de origen. Lee y calcula.
* No propone umbrales. Produce la distribución; **la decisión es de Dirección** (§11.4).
* No elige base de datos. El catálogo vive en archivos planos hasta que exista `erp/`; cuando
  exista, cambia `services/masterdata/loader.py` y nada más — los servicios de cálculo reciben un
  `Catalogo`, no un archivo.

## Requisito de salida hacia la Fase 1

El procedimiento completo está en [umbrales.md](umbrales.md). Lo que la Fase 0 aporta:

| Paso | Qué produce el código |
|---|---|
| 1. Margen real sobre ≥1 trimestre | `distribucion_margen` del reporte: mínimo, p25, mediana, p75, máximo y ponderado |
| 2. Propuesta de `margen_objetivo_pct` y `margen_minimo_pct` | La distribución por ruta (`margen_por.ruta`), más las `desviaciones_tarifa`: dónde el margen mínimo que la tabla promete no es el que la operación entrega |
| 3. Autorización de Dirección | Fuera del código. Queda en `svc-runlog` a partir de la Fase 1 |
| 4. Contraste de umbrales contra histórico | Requiere el histórico cargado por `svc-ingest` |

Además de los umbrales, la Fase 1 exige la bandeja de HITL en producción y
`validate_registry.py` en verde (§17.5). El validador ya corre en verde con las reglas aplicables
hoy; seis quedan **omitidas** —no en verde— porque dependen de agentes o del catálogo de
habilidades, que aún no existen.

## Cobertura de pruebas

```
tests/unit/test_masterdata.py       carga, integridad referencial, vigencia de tarifas
tests/unit/test_ingest.py           alias, cuarentena, derivaciones, dedupe, haversine
tests/unit/test_costing.py          los tres tests del contrato §10.2, más desglose y supuestos
tests/unit/test_profitability.py    margen, ponderación, percentiles, contraste de tarifas
tests/integration/                  la fase completa sobre data/ejemplo, incluido determinismo
tests/validation/                   registry/ contra las reglas de §10.3
```

La regla 7b del validador cierra el círculo: **todo test que un contrato declara tiene que existir
de verdad en `tests/`.** Un contrato no puede prometer una prueba que nadie escribió.
