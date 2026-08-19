# La oficina virtual

Dieciséis puestos con nombre, memoria y límites. Nueve consultores que construyen el ERP, tres
agentes de Tecnología y —desde el cierre de las fases 1 y 2— cuatro agentes de operación.
Un plano en píxeles para verlos trabajar.

**Ninguno de los doce que están encendidos declara un solo `ACT-*`.** Esa es la propiedad que
hace seguro encenderlos antes de tiempo: siguen sin poder escribir en la operación, emitir un
documento o mandar un correo. Producen texto y código, que es exactamente lo que hace falta
para terminar el ERP.

Los otros cuatro —`D4-03`, `D2-03`, `D3-05` y `D2-04`— están **`listo`**: contrato completo,
prompt escrito, memoria puesta y encendido pendiente. `D4-03` declara un `ACT-EMAIL-S` y `D2-04`
declara además `ACT-DOC-S`, y por eso mismo no se encienden hasta cerrar sus condiciones. Ver
[fase-1.md](fase-1.md) y [fase-2.md](fase-2.md).

## Tres estados, no dos

| Estado | Qué significa | En el plano |
|---|---|---|
| `planned` | El agente no existe todavía: su fase no llegó | Silla vacía |
| `listo` | Existe entero y nadie puede convocarlo: le faltan condiciones de entrada escritas en su registro | Silla preparada, sin nadie |
| `built` | Encendido. Se le puede convocar | Alguien sentado |

El estado intermedio no es un matiz burocrático. Un agente terminado y apagado es una situación
legítima y peligrosa: el trabajo está hecho, nadie lo usa y en dos semanas nadie recuerda por qué.
Por eso `listo` obliga a declarar `condiciones_encendido` con condición, responsable y estado, y
**la regla 13 del validador falla** si alguien deja el adjetivo sin la lista — o si todas las
condiciones están cumplidas y el agente sigue apagado.

## Por qué estos agentes y no otros

| | |
|---|---|
| `C-01`…`C-09` | **No se adelantaron: nunca tuvieron fase.** La §5-bis.3 lo dice literal: "no hay fase de roadmap que los encienda; existen desde que el registro los declara". Lo que faltaba era hacerlos ejecutables, no autorizarlos |
| `D5-01` Producto ERP | Adelantado de la fase 7 a la 0. Es quien convoca a los consultores y quien integra lo que devuelven (§5-bis.3.1 y .4). Sin él, la capa de consultoría no tiene a quién entregarle |
| `D5-03` AgentOps | Adelantado por la regla que el propio roadmap escribe: se enciende "en cuanto haya más de ~8 agentes activos". Con doce, ya se cruzó |
| `D5-02` Datos e Insights | **No se adelantó.** Todo lo que consume nace en la fase 3 o después. Encenderlo sería un agente sin datos que leer |

El adelanto está escrito en el registro, no sólo aquí: cada agente declara `adelantado_a` y
`razon_adelanto`, y la regla 12 del validador falla si alguien adelanta un agente sin decir por qué
—o si un agente adelantado se atreve a declarar un `ACT-*`.

## Quién es quién

| | Agente | Rol | Cómo trabaja |
|---|---|---|---|
| **Renata** | `C-01` | Producto y UX | Pregunta por la persona antes que por la pantalla |
| **Iker** | `C-02` | Frontend y Design System | Consistencia antes que novedad |
| **Bruno** | `C-03` | Backend y Lógica | Piensa en el error antes que en el camino feliz |
| **Dalia** | `C-04` | Modelo de Datos | Normaliza, nombra y documenta |
| **Simón** | `C-05` | Integraciones y APIs | Desconfía de todo sistema ajeno |
| **Vera** | `C-06` | Seguridad y Accesos | Asume que alguien ya está adentro |
| **Tomás** | `C-07` | QA y Testing | Convierte requerimientos en criterios verificables |
| **Nadia** | `C-08` | DevOps y Continuidad | Pregunta cómo se revierte, no cómo se despliega |
| **Elena** | `C-09` | Documentación Técnica | Escribe para quien llegue en seis meses |
| **Mateo** | `D5-01` | Producto y Requerimientos ERP | Traduce operación a requerimiento y ordena el backlog |
| **Paula** | `D5-02` | Datos e Insights | Silla vacía hasta la fase 3 |
| **Aurora** | `D5-03` | AgentOps | Mira la bitácora de todos: calidad, costo y deriva |
| **Ivana** | `D4-03` | Pricing y Propuestas | Redacta sobre el precio que calcula `svc-pricing`. Listo, sin encender |
| **Rubén** | `D2-03` | Costos y Márgenes | Explica el costo por km y el margen que produce la Fase 0. Listo, sin encender |
| **Sofía** | `D3-05` | Evidencias y Cierre de Viaje | Persigue el papel que falta. Listo, sin encender |
| **Ximena** | `D2-04` | Ciclo de Ingreso | Prepara el comprobante y sigue la cobranza. Listo, sin encender |

La identidad vive en [`office/identidades.yaml`](../office/identidades.yaml); la autoridad, en
`registry/`. Cuando se contradigan, manda el registro.

## Memoria y habilidades

Cada agente tiene un archivo en [`agents/memoria/`](../agents/memoria/): sus habilidades y sus
notas fechadas, ligadas al encargo que las produjo. Es Markdown versionado en git a propósito —
una memoria que sólo el sistema puede leer es una memoria que nadie audita, y esta se revisa en
un diff como cualquier otro cambio.

El prompt de cada agente **se genera**, no se escribe: contrato común
([`agents/base.md`](../agents/base.md)) + registro + identidad + memoria. Editarlo a mano crearía
una segunda verdad que nadie sincroniza. Salen a [`agents/prompts/`](../agents/prompts/) para
poder leerlos y versionarlos.

## Cómo se convoca a alguien

```bash
python -m office.cli convocar C-04 \
  --titulo "Esquema de la tabla de tarifas" \
  --descripcion "Módulo: datos. Problema: falta vigencia. Restricción: no migrar los CSV." \
  --entregable "Esquema, migración y diccionario" \
  --por D5-01
```

El runtime aplica las reglas **antes** de que el modelo hable:

1. Sólo Dirección o `D5-01` convocan a un consultor (§5-bis.3.1). A cualquier otro lo rechaza.
2. Un encargo sin módulo, problema o entregable no arranca (§5-bis.3.2): el agente pediría
   contexto de todos modos, así que se pide antes de gastar tokens.
3. Un consultor con `ACT-*` es un error de modelado, y se verifica en cada convocatoria.
4. Un agente cuya fase no llegó no acepta encargos.
5. Un agente `listo` los rechaza **diciendo cuál de sus condiciones falta y quién la cierra**.
   "No disponible" a secas sería la peor respuesta posible: la que nadie puede accionar.
6. Toda convocatoria abre un `trace_id` en `svc-runlog` (§5-bis.3.5).

Otros comandos:

```bash
python -m office.cli estado                     # quién está haciendo qué, en texto
python -m office.cli avanzar E-002 en_curso --autor Dalia --nota "empieza el esquema"
python -m office.cli recordar C-04 "la tarifa necesita vigencia" --tipo decision --encargo E-002
python -m office.cli build                      # regenera el plano y los prompts
```

## El plano

[`office/oficina.html`](../office/oficina.html) se abre con doble clic: el estado viaja dentro del
archivo, sin servidor y sin `fetch`. Se regenera con `python -m office.cli build`.

Lo que se ve **es el estado del repositorio**, no una animación decorativa:

| En el plano | Sale de |
|---|---|
| Tecleando | un encargo `en_curso` del agente |
| Levanta la mano | un encargo `bloqueado`: falta contexto o falta una aprobación humana |
| Escritorio iluminado | el agente tiene trabajo abierto |
| Silla vacía | el agente está `planned`; su fase no llegó |
| Silla preparada | el agente está `listo`: existe entero y sus condiciones de encendido siguen abiertas |
| Ficha lateral | registro + identidad + memoria + encargos, al hacer clic |
| Bitácora | `svc-runlog`, append-only — el mismo registro que usan los casos de negocio |

## Encargos: el backlog del ERP

Los doce encargos de [`office/encargos/`](../office/encargos/) son el camino para terminar el ERP,
y su primer hito es la **bandeja única de HITL** — que no es un módulo más: es requisito de
entrada de la Fase 1 (§17.5). Si algo se pospone, no es eso.

Los estados y sus transiciones son estrechos a propósito: `pendiente → en_curso → hecho`, con
`bloqueado` a los lados. Cada cambio queda en la bitácora con el `trace_id` del encargo; un cambio
de estado sin rastro no vale (R7).

Los cuatro estados de la oficina son una vista de los ocho de `svc-runlog`, y la traducción no es
libre: `hecho` no es una transición, es un camino. Cerrar un encargo escribe en el registro el
paso por validación —y por la bandeja humana si el encargo es `hitl`— porque la máquina de
estados del servicio no permite el atajo. La oficina no puede darse por entregada sin pasar por
donde la arquitectura dice.

## Qué es y qué no es esto

**Es** la infraestructura de gobierno de los agentes: identidad, memoria, reglas de convocatoria,
trazabilidad y un plano para mirarla. Todo verificable y versionado.

**No es** un runtime de LLM. `armar_contexto()` construye el prompt completo de un agente y ahí se
detiene: quien razona hoy es Claude Code, que es literalmente como el organigrama describe al
equipo de `T05-02` ("ingeniería humana asistida con Claude Code"). Cuando exista un runtime
propio, se conecta en ese punto y ni las reglas ni la memoria cambian.

## La bitácora ya no es un registro aparte

Hasta la Fase 1, `office/bitacora.jsonl` era el precursor declarado de `svc-runlog`. Con el
servicio construido, mantener los dos habría sido justo lo que la arquitectura no permite: dos
respuestas posibles a "¿qué le pasó a este caso?" sin nadie que garantice que cuadran.

[`office/bitacora.py`](../office/bitacora.py) es hoy **una vista de `svc-runlog`**: cada evento
de oficina se escribe como un paso del caso, y los cambios de estado como transiciones reales.
Lo que la oficina gana es que ya puede preguntar `progreso_de(trace)` en vez de interpretar una
lista de eventos, y que el costo en tokens de un encargo se lee en el mismo lugar que el de una
cotización.

El archivo viejo se importó con [`scripts/migrar_bitacora.py`](../scripts/migrar_bitacora.py),
conservando fecha y `trace_id` de cada evento —rellenarlos con la fecha de la importación habría
convertido el histórico en ruido— y **no se reescribió ni se borró**: se queda donde está, que es
lo que corresponde a un registro append-only. La importación es idempotente.

Una consecuencia que conviene decir en voz alta: el registro vive en `data/runlog/`, que está en
`.gitignore`. La bitácora de la oficina dejó de versionarse en git a partir de la migración,
igual que el resto de los datos de operación. El histórico congelado hasta ese momento sigue
versionado en `office/bitacora.jsonl`.
