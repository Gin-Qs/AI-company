# El portal de mando

> Este documento es el entregable de `E-012` — *"Alcance del MVP del ERP para autorización
> de Dirección"*, el encargo que está `bloqueado` esperando exactamente esto.
>
> **Estado: Fase 0 en marcha.** Construidos y verificados: la CI (§11), el puerto del
> calendario laboral a TypeScript (§8.1), y el calendario y los SLA convertidos en
> configuración leída desde YAML por las dos implementaciones. Falta `migrar_a_postgres.py`
> (§9), que necesita que exista la base de datos. Las Fases A–C esperan las cuentas y la
> decisión de §7.2.

## 1. Qué es esto, en una frase

El portal no es un tablero nuevo que se añade al proyecto: **es la bandeja única de HITL**
que la arquitectura v3 §7.2 congeló como decisión, que doce encargos abiertos están
construyendo desde agosto, y que los cinco agentes del MVP declaran como condición de
encendido en su propio registro.

Verificado en el repositorio, no supuesto:

```
$ grep -l "Bandeja única de HITL del ERP en producción" registry/agents/*.yaml
registry/agents/D1-03-sintesis-ejecutiva.yaml
registry/agents/D2-03-costos-y-margenes.yaml
registry/agents/D2-04-ciclo-de-ingreso.yaml
registry/agents/D3-05-evidencias-y-cierre-de-viaje.yaml
registry/agents/D4-03-pricing-y-propuestas.yaml
```

Los cinco. `responsable: D5-01`, `cumplida: false`, `donde: office/encargos/E-001.yaml`.

Eso cambia cómo se lee todo lo que sigue. Este portal no compite por prioridad con el
encendido de los agentes: **es el encendido de los agentes.** Mientras no exista, ninguno de
los cinco puede convocarse, y `agents/runtime.py` seguirá rechazando la convocatoria
nombrando esta condición. Terminar el portal no "habilita un dashboard": tacha una casilla en
cinco archivos del registro y desbloquea el MVP completo.

Y los doce encargos ya escritos son su plan de trabajo, no un proyecto paralelo:

| Encargo | Estado | Agente | Qué aporta al portal |
|---|---|---|---|
| `E-001` | en_curso | D5-01 | Requerimientos de la bandeja con criterio de aceptación |
| `E-002` | en_curso | C-04 | Esquema de datos v1 → **§6 de este documento** |
| `E-003` | pendiente | C-03 | Servicios y reglas de negocio del módulo HITL → **§8** |
| `E-004` | pendiente | C-01 | Flujo de pantalla de la bandeja → **§10** |
| `E-005` | pendiente | C-02 | Componentes y design system del panel |
| `E-006` | pendiente | C-05 | Integraciones (Airtable, GPS, banca) — fuera de este corte |
| `E-007` | pendiente | C-06 | Matriz de roles y accesos → **§7** |
| `E-008` | pendiente | C-07 | Criterios de aceptación y regresión → **§13** |
| `E-009` | pendiente | C-08 | Ambientes, despliegue y respaldo → **§5, §12** |
| `E-010` | pendiente | C-09 | Diccionario de datos y guía de onboarding |
| `E-011` | pendiente | D5-03 | Evaluación de calidad de los entregables de consultoría |
| `E-012` | **bloqueado** | D5-01 | Alcance del MVP para autorización de Dirección → **este documento** |

## 2. Correcciones al plan original

Cuatro afirmaciones del borrador no sobrevivieron a la verificación contra el repositorio. Se
listan porque un plan que corrige en silencio enseña a no verificar el siguiente.

**2.1 — Son 16 reglas, no 14.** *(hoy 17: ver §17)* `scripts/validate_registry.py` define dieciséis funciones
(`regla_1` … `regla_13`, más `3b`, `7b`, `7c`). El "14" del borrador salió de leer el resumen
de la última línea:

```
14 en verde, 0 en falla, 2 omitidas
```

Las dos omitidas —regla 1 y regla 4, ambas sobre el catálogo de habilidades— no están mal:
están **omitidas por falta de insumo**, que es un tercer estado. La vista de salud del
registro (§10, vista 7) necesita cuatro estados —verde, falla, omitida, pendiente-de-fase-
futura— y no un semáforo binario. Un validador que pinta "omitida" de verde miente por
optimismo; uno que la pinta de rojo entrena al equipo a ignorar el rojo.

**2.2 — El estado operativo no vive sólo en archivos ignorados por git.** El borrador dedujo,
correctamente, que `data/runlog/*.jsonl` está en `.gitignore` y por tanto nunca fue pensado
para versionarse. Pero generalizó de más. El inventario real:

| Artefacto | En git | Lo escribe | Mutable |
|---|---|---|---|
| `data/runlog/runlog.jsonl` | **no** (`.gitignore`) | `svc-runlog`, `office/bitacora.py` | sí, append-only |
| `office/encargos/*.yaml` (12) | **sí** | `office.cli convocar` / `avanzar` | **sí** |
| `agents/memoria/*.md` (16) | **sí** | `office.cli recordar` | **sí**, append-only |
| `office/pausa.yaml` | **sí** | a mano / Dirección | **sí** |
| `office/bitacora.jsonl` | **sí** | nadie ya — histórico congelado | no |
| `agents/prompts/*.md` (16) | **sí** | `office.cli build` | generado |
| `office/oficina.html` | **sí** | `office.cli build` | generado |

Tres de esos —encargos, memoria y pausa— son estado operativo vivo, escrito por el CLI, y
versionado en git. El borrador los daba implícitamente por "configuración declarada". No lo
son, y esa confusión era el hueco central del plan: sin resolverla, el portal y el CLI se
vuelven dos verdades sobre el mismo hecho. §4 lo resuelve.

**2.3 — Sí hay historia que migrar.** El borrador afirma *"nada se ha encendido todavía, así
que no hay historia real de casos que migrar; Postgres arranca vacío"*. Hay **12 encargos con
`trace_id`, 42 eventos en el runlog y 20 entradas de bitácora ya importadas** por
`scripts/migrar_bitacora.py`. Es poco, pero no es cero, y arrancar vacío haría fallar la
propia prueba de verificación que el borrador propone: comparar el portal contra
`python -m office.cli estado`. La siembra inicial es un paso obligatorio (§9), no un detalle.

**2.4 — No existe CI.** No hay `.github/`. Toda la validación del repositorio ocurre hoy en
la máquina de quien programa, a mano. El borrador daba por hecho que "un cambio en
`budget.yaml` vía PR dispara un redeploy que recoge la política nueva" — cierto para Vercel,
pero **nada valida ese PR antes de desplegarlo**. Hoy un YAML mal escrito llega a producción
sin que nadie corra el validador. Construir la CI deja de ser un extra: es un prerrequisito
de §11.

## 3. Dónde vive cada cosa

La regla que ordena el resto: **Vercel ejecuta funciones serverless, sin disco persistente
entre invocaciones.** Todo lo que hoy se escribe en un archivo tiene que decidirse.

| Qué | Dónde vive después del portal | Por qué |
|---|---|---|
| Contratos de agentes, servicios, equipos y consultores (`registry/`) | **git**, sin cambios | Cambia por PR, se valida con las reglas del validador, se audita en el historial. El portal la lee, nunca la escribe |
| Políticas (`budget`, `authority-gate`, `calendario-laboral`, `rubrica-*`, `alertas`, `kpis`…) | **git**, sin cambios | Igual. Un umbral que se puede cambiar desde una pantalla es un umbral sin auditoría |
| Identidades y zonas (`office/identidades.yaml`) | **git**, sin cambios | Es cómo se ve y cómo suena un agente. No es estado |
| Habilidades declaradas de cada agente | **git** (en el registro) | Se siembran desde el perfil; no las escribe la operación |
| Casos, pasos, transiciones, HITL, consumo (`runlog`) | **Postgres** | Ya estaba fuera de git. Necesita escrituras concurrentes de varias personas |
| **Encargos** | **Postgres** | Decisión de §4 |
| **Notas de memoria** de cada agente | **Postgres** | Decisión de §4 |
| **Pausa de la oficina** | **Postgres** | Decisión de §4 |
| Resultado del validador y de `pytest` | **Postgres**, escrito por CI | §11 |
| `office/bitacora.jsonl` | **git**, congelado | Histórico ya importado. Se conserva como evidencia del origen, no se vuelve a leer |

Se preserva la filosofía event-sourced de `svc-runlog` (§8 de la arquitectura: *"los casos no
se guardan como filas que se actualizan: se reconstruyen plegando los eventos"*). La tabla de
eventos pasa de ser un archivo `.jsonl` a ser una tabla de Postgres, y nada más cambia en el
modelo.

## 4. La decisión que el borrador no tomaba: encargos, memoria y pausa

**Postgres se vuelve la verdad operativa. El CLI de Python conserva sus comandos de lectura y
pierde los de escritura.**

Concretamente, después de la migración:

| Comando | Hoy | Después |
|---|---|---|
| `office.cli estado` | lee YAML + JSONL | lee Postgres. Misma salida |
| `office.cli build` | genera HTML y prompts | igual, leyendo Postgres |
| `office.cli convocar` | escribe `office/encargos/E-0NN.yaml` | **sólo-desarrollo**: exige `AI_COMPANY_ENTORNO=local` y falla en cualquier otro |
| `office.cli avanzar` | reescribe el YAML | idem |
| `office.cli recordar` | escribe `agents/memoria/*.md` | idem |
| `services.cli` (fase0, cotizar, facturar, cartera, brief) | no toca nada de esto | **sin cambios** |

Los cinco comandos de `services.cli` son cálculo puro sobre `data/ejemplo`: no escriben estado
operativo y no se tocan. Las pruebas siguen corriendo contra archivos, en `tmp_path`,
exactamente como hoy.

**Qué se pierde y por qué se acepta.** Los 12 encargos y las 16 memorias dejan de tener su
historia en `git log`. Se acepta porque a cambio se gana lo que git nunca dio aquí: dos
personas actuando a la vez sin pisarse, y un autor real en cada acción. Hoy el `--autor` del
CLI es texto libre —cualquiera escribe `--autor Gabriel`— y esa es la razón principal por la
que el Gate de Autoridad existe en el papel y no en la operación, que es literalmente lo que
`E-001` dice del sistema actual. Clerk cierra ese hueco.

**Qué se conserva.** Los archivos actuales **no se borran**. Quedan en el repositorio como el
estado congelado del día de la migración, igual que se hizo con `office/bitacora.jsonl`: el
origen de un dato importado tiene que poder mirarse. Un `README` en `office/encargos/` dice
desde cuándo dejaron de ser la verdad.

**La excepción que no se hizo.** Se consideró dejar la pausa en git —es el control de máximo
privilegio y se escribe casi nunca— pero se descartó: `agents/runtime.py:convocar()` lee
`office/pausa.yaml` en cada convocatoria, y si el portal pausara en Postgres mientras el
runtime lee un YAML, la pausa no pausaría. Dos verdades sobre el control más importante del
sistema es exactamente el error que este documento existe para evitar. La pausa se va a
Postgres con todo lo demás, y `office/estado.py:leer_pausa()` cambia de fuente.

## 5. Repositorio y despliegue

Mismo monorepo. Carpeta nueva `web/` con Next.js (App Router, TypeScript). Vercel se
configura con **root directory = `web/`**.

```
AI-company/
  registry/  agents/  services/  office/  docs/   <- Python, sin cambios de arquitectura
  scripts/
    validate_registry.py                          <- la fuente de verdad de las 16 reglas
    vectores_sla.py                               <- genera los vectores dorados (§8.1)
    migrar_a_postgres.py                          <- POR ESCRIBIR: la siembra de §9
  tests/fixtures/sla-vectores.json                <- el contrato del calendario laboral
  .github/workflows/validar.yml                   <- POR ESCRIBIR: §11
  web/
    app/
      (dashboard)/resumen|agentes|hitl|casos|registro|presupuesto|oficina/
      api/                                        <- route handlers, RBAC del lado servidor
    lib/
      registro.ts     <- lee registry/*.yaml y office/identidades.yaml (fs, sólo lectura)
      rbac.ts         <- persona Clerk -> autoridad, derivado de los YAML (§7)
      db/             <- cliente Postgres y consultas del event log
      reglas/         <- puertos de services/runlog y services/budget (§8)
    prisma/
      schema.prisma   <- traducción del esquema de §6
```

**Vercel necesita ver `registry/` desde `web/`.** Con root directory = `web/`, el build por
defecto no incluye archivos de arriba. Se resuelve declarando `outputFileTracingIncludes` en
`next.config.js` para `../registry/**` y `../office/identidades.yaml`. Sin eso,
`lib/registro.ts` compila en local y devuelve "archivo no encontrado" en producción — un
fallo que sólo aparece después del despliegue.

## 6. Esquema de la base de datos

El contrato de `E-002`. Postgres, `numeric` para todo lo monetario —nunca `float`, ver §8.3.

```sql
-- Quién es quién. El puente entre Clerk y los nombres que ya viven en los YAML.
-- No guarda rol: el rol se deriva en cada request (§7). Una copia del rol aquí sería
-- una segunda verdad que nadie sincroniza cuando cambie un owner en registry/teams/.
create table personas (
  id             uuid primary key default gen_random_uuid(),
  clerk_user_id  text unique,            -- null hasta que la persona acepte la invitación
  nombre         text unique not null,   -- debe existir en authority-gate.yaml (§7.3)
  activa         boolean not null default true,
  invitada_por   uuid references personas(id),
  creada_en      timestamptz not null default now()
);

-- EL REGISTRO. Append-only, inmutable, la traducción directa de data/runlog/runlog.jsonl.
-- No hay UPDATE ni DELETE sobre esta tabla: se revocan por permisos, no por disciplina.
create table eventos (
  id             bigserial primary key,
  trace_id       text        not null,
  seq            integer     not null,   -- orden dentro del caso; ver la unique de abajo
  evento         text        not null check (evento in ('apertura','paso','transicion')),
  ts             timestamptz not null,
  actor          text        not null,   -- agente (D4-03) o servicio (svc-runlog)
  autor_persona  uuid references personas(id),  -- quién lo hizo, si fue una persona
  datos          jsonb       not null,   -- el resto del evento, tal como lo define caso.py
  unique (trace_id, seq)
);
create index on eventos (trace_id, seq);
create index on eventos (ts);

-- Proyección de casos. Se reconstruye plegando `eventos` y se actualiza en la MISMA
-- transacción que el append. Existe por velocidad de consulta, no como fuente: si
-- divergiera, se tira y se vuelve a plegar. Eso es lo que la hace segura.
create table casos (
  trace_id        text primary key,
  tipo            text not null,          -- cotizacion, cierre_de_viaje, encargo, brief...
  referencia      text not null,          -- T-1001, CL-01, E-001...
  criticidad      text not null check (criticidad in ('alta','media','baja')),
  estado          text not null check (estado in (
                    'recibido','en_proceso','esperando_validacion','rechazado_validacion',
                    'esperando_humano','entregado','bloqueado','expirado')),
  responsable     text not null default '',
  abierto_en      timestamptz not null,
  actualizado_en  timestamptz not null,
  reintentos      integer not null default 0,   -- tope 2: services/runlog/caso.py
  escalamientos   integer not null default 0,
  pasos           integer not null default 0,
  tokens          bigint  not null default 0,
  costo_mxn       numeric(14,2) not null default 0,
  ultimo_seq      integer not null default 0    -- el candado optimista, ver §8.4
);
create index on casos (estado, actualizado_en);

-- Encargos. Proyección igual que `casos`: su historia son eventos, no columnas mutables.
create table encargos (
  id                   text primary key,   -- E-013 en adelante; E-001..E-012 se importan
  titulo               text not null,
  agente               text not null,      -- debe existir en registry/agents o consultants
  convocado_por        uuid not null references personas(id),
  estado               text not null check (estado in
                         ('pendiente','en_curso','bloqueado','hecho')),
  descripcion          text not null default '',
  entregable_esperado  text not null default '',
  depende_de           text[] not null default '{}',
  hitl                 boolean not null default false,
  trace_id             text not null references casos(trace_id),
  creado_en            timestamptz not null default now(),
  actualizado_en       timestamptz not null default now()
);

-- Memoria de agente. Sólo las notas: las habilidades siguen viniendo del registro en git.
create table memoria_notas (
  id         bigserial primary key,
  agente     text not null,
  fecha      date not null,
  encargo    text not null default '-',
  tipo       text not null check (tipo in
               ('decision','supuesto','trampa','aprendizaje','contexto')),
  texto      text not null,
  trace_id   text references casos(trace_id),
  autor      uuid references personas(id),
  creada_en  timestamptz not null default now()
);
create index on memoria_notas (agente, fecha desc);

-- Pausa de la oficina. El motivo y su levantamiento viven en la MISMA fila, igual que en
-- office/pausa.yaml: si vivieran separados, en un mes nadie sabría si se levantó porque se
-- cumplió la condición o porque hacía falta trabajar.
create table pausa (
  id                 bigserial primary key,
  desde              timestamptz not null default now(),
  por                uuid not null references personas(id),
  motivo             text not null,
  se_reanuda_cuando  text not null,
  hasta              timestamptz,
  reanudada_por      uuid references personas(id),
  reanudada_porque   text
);
-- La oficina está en pausa si existe una fila con hasta IS NULL. Como máximo una:
create unique index pausa_activa_unica on pausa ((true)) where hasta is null;

-- Salud del registro. La escribe la CI (§11); el portal sólo la lee.
create table validacion_registro (
  id            bigserial primary key,
  commit_sha    text not null,
  rama          text not null,
  corrido_en    timestamptz not null default now(),
  reglas        jsonb not null,   -- [{numero, descripcion, estado, fallas, pendientes}]
  en_verde      integer not null,
  en_falla      integer not null,
  omitidas      integer not null,
  pendientes    integer not null,
  pytest_ok     boolean not null,
  pytest_total  integer
);
create index on validacion_registro (rama, corrido_en desc);
```

**Lo que a propósito NO es una tabla.** El consumo de presupuesto por agente y periodo: se
calcula agregando `eventos` (`svc-runlog` provee el consumo, `svc-budget` sólo compara — es la
regla 3 del encabezado de `services/budget/control.py`). Una tabla de consumo sería la segunda
fuente que ese servicio existe para no tener.

## 7. RBAC: de una cuenta de Clerk a una autoridad

El rol no se inventa ni se guarda: se **deriva en cada request** cruzando el nombre de la
persona contra dos fuentes que ya existen en git.

```
Clerk userId → personas.nombre → ┬→ registry/policies/authority-gate.yaml → rol
                                 └→ registry/teams/*.yaml                 → alcance
                                       ↑
              registry/agents/*.yaml (agente → teams) resuelve de qué equipo es un HITL
```

**7.1 La cadena, resuelta.** Un HITL vive sobre un `trace_id`; el caso declara su `actor` (el
agente); el agente declara sus `teams`; el equipo declara su `owner_humano`. Y
`authority-gate.yaml → hitl.ruteo: owner_humano_del_equipo` dice que ahí se enruta.

Aplicado a los ocho agentes del registro — derivado del repositorio, no propuesto:

| Agente | Estado | Equipo | Aprueba (`owner_humano`) | Ven y pueden actuar (`co_owners`) |
|---|---|---|---|---|
| D1-03 | listo | T01-03 | Gabriel | Nay, Ana |
| D2-03 | listo | T02-02 | Nay | Gabriel |
| D2-04 | listo | T02-04 | Nay | Ana, Gabriel |
| D3-05 | listo | T03-06 | **Elias** | Ana, Gabriel |
| D4-03 | listo | T04-03 | **Gabriel** | Nay, Ana |
| D5-01 | built | T05-01 | Gabriel | — |
| D5-02 | planned | T05-03 | Gabriel | Nay |
| D5-03 | built | T05-04 | Gabriel | — |

**7.2 Una contradicción del registro que este ejercicio destapó. `[RESUELTA]`**

*Corrección respecto de la primera versión de este documento: ahí se afirmó que Ana no era
`owner_humano` de ningún equipo. Es falso.* Ana responde por **T04-04, T07-01 y T07-05**. Lo
que ocurre es que los agentes de esos tres equipos —`D4-04`, `D7-01`, `D7-03`— son de fases
futuras y todavía no tienen archivo en `registry/agents/`. El efecto práctico es el mismo y
la contradicción es real: **hoy ningún agente existente le enruta un HITL a Ana**, mientras
el gate le atribuye autoridad sobre dos umbrales que pertenecen a `D4-03`, que sí existe y
rutea a Gabriel.

Pero `authority-gate.yaml` le da autoridad explícita de aprobación en dos umbrales:

```yaml
descuento_tarifa:
  humano_operativo: { max_pct: 5, quien: Ana }
plazo_de_pago:
  humano_operativo: { max_dias: 45, quien: Ana }
```

Ambos son el dominio de `D4-03` (Pricing y Propuestas), cuyo equipo `T04-03` tiene
`owner_humano: Gabriel`. Así que la tabla de autoridad dice "un descuento de 3% lo aprueba
Ana" y la regla de ruteo dice "el HITL de D4-03 le llega a Gabriel". Las dos no pueden ser
verdad.

**Resuelto convirtiendo el ruteo en configuración.** Dirección aprobó la salida que no
descarta ninguna autoridad ya declarada. `hitl.ruteo` dejó de ser un valor suelto y ahora
separa dos preguntas que no son la misma:

```yaml
hitl:
  ruteo:
    responsable: owner_humano_del_equipo      # a quién le llega y quién RESPONDE
    aprueban_ademas: co_owners_con_autoridad  # quién más puede APROBARLO
    comodin_direccion: true                   # Dirección puede aprobar cualquier HITL
```

Con `co_owners_con_autoridad`, Ana puede aprobar un descuento del 3% de `D4-03` —porque
`descuento_tarifa.humano_operativo.quien` la nombra— y **no** puede aprobar uno del 8%, que
es de Dirección. Gabriel sigue siendo el responsable del equipo: la responsabilidad no se
diluye, sólo se reconoce que la autoridad ya escrita en `umbrales` sirve para algo.

Los otros dos valores admitidos —`nadie` y `co_owners`— quedan documentados en el YAML. Si
mañana el criterio cambia, se cambia ahí, no en el código.

Implementado en `web/lib/rbac.ts` y cubierto por 24 pruebas que corren contra el registro
real: si alguien cambia un `owner_humano` y con eso deja a una persona sin poder aprobar lo
que el gate le atribuye, la suite se pone roja.

**7.3 Los externos.** `authority-gate.yaml` declara `externos: [contador, abogado]` —
etiquetas de puesto, no nombres de persona. `personas.nombre` debe coincidir con un valor de
`autoridades`, así que un contador entra al portal con `nombre = "contador"`. Funciona
mientras haya uno de cada. Dos contadores obligan a cambiar el YAML, no la base de datos, y
eso es correcto: quién tiene qué autoridad es una decisión de registro.

Su alcance es lectura, y no por configuración del portal sino por construcción: no son
`owner_humano` de nada, así que la derivación no les devuelve ningún equipo sobre el que
actuar. La regla dura *"Ningún externo tiene autoridad de aprobación en el Gate"* se cumple
sin una línea de código que la imponga — que es la única forma en que una regla dura se cumple
de verdad.

**7.4 Autenticación.** Clerk en modo restringido (invite-only), sin registro público. Cada
persona la invita un admin. Middleware de Clerk por defecto-denegado sobre todo `(dashboard)`;
sólo la página de login es pública. Una persona autenticada en Clerk pero sin fila en
`personas` **no entra**: ve una pantalla que dice que su cuenta existe y no está vinculada a un
nombre del registro. Autenticado no es autorizado.

## 8. El puerto de las reglas de negocio a TypeScript

Cuatro piezas de Python se reimplementan. En las cuatro, el riesgo no es que fallen: es que
funcionen *casi* igual. Un SLA que se corre media hora no truena — aprueba tarde y parece
correcto.

**8.1 El calendario laboral. `[CONSTRUIDO]`** Era el más frágil, y por dos razones. La
primera: el huso, la jornada y los días hábiles vivían **en duro** dentro de `sla.py`, y
`authority-gate.yaml` declaraba los mismos plazos de SLA **sin que nadie los leyera** —
cambiar el SLA en la política no cambiaba nada. La segunda: Vercel corre en UTC, y un puerto
que olvide convertir pondría la jornada de las 3 de la mañana al mediodía.

Las dos están cerradas. Ahora hay **una fuente por cosa**, y las dos implementaciones la leen:

| Qué | Dónde se declara | Quién la lee |
|---|---|---|
| Huso, jornada, días hábiles, festivos | `registry/policies/calendario-laboral.yaml` | `services/runlog/sla.py` · `web/lib/registro/politicas.ts` |
| Plazo y consecuencia por criticidad | `registry/policies/authority-gate.yaml` → `hitl.sla` | las mismas dos |

Cambiar el horario de la oficina o un plazo de SLA es editar un YAML y abrir un PR. No se
toca código. Y `tests/unit/test_calendario.py` (12 pruebas) comprueba que la configuración
**configura de verdad**: cada prueba cambia una línea del YAML y exige que el comportamiento
cambie con ella — porque un archivo de política que el código carga pero ignora se ve igual
que uno que respeta, hasta el día que alguien cambia un número y no pasa nada.

El contrato entre las dos implementaciones es **`tests/fixtures/sla-vectores.json`**, generado
desde el Python real por `scripts/vectores_sla.py`. Lleva diecisiete vectores **y la
configuración con la que se generaron**, así que el puerto no sólo reproduce los resultados:
comprueba que está leyendo los mismos YAML. Acertar con la configuración equivocada sería
acertar por suerte.

```
alta   2026-06-05T21:30:00Z  ->  2026-06-08T10:30:00-06:00 (lunes)
alta   2026-06-06T18:00:00Z  ->  2026-06-08T13:00:00-06:00 (lunes)
baja   2026-06-04T20:00:00Z  ->  2026-06-09T14:00:00-06:00 (martes)
```

Las dos implementaciones se prueban contra el mismo archivo. Si `sla.py` cambia, se regeneran
los vectores y el test de TypeScript falla hasta que el puerto se actualice — la deriva se
vuelve un test rojo en vez de una aprobación tardía.

Los siete vectores de `decisiones_al_vencer` cubren la regla dura: ninguna acción al vencer es
"aprobar", ni con cero escalamientos ni con dos.

**8.2 La máquina de estados (`services/runlog/caso.py`).** Ocho estados, `TRANSICIONES` como
tabla, `MAX_REINTENTOS = 2`. Se traduce literal, y se valida en dos lugares: en el `check` de
la columna `casos.estado` (§6) y en la ruta server-side antes de escribir. La regla de que el
tercer rechazo bloquea el caso es aritmética, no criterio: se copia tal cual.

**8.3 El dinero.** Python usa `Decimal` con `mxn()` cuantizando a dos decimales. JavaScript
sólo tiene `float64`, y `0.1 + 0.2 !== 0.3`. **Ningún importe cruza el sistema como
`number`**: `numeric` en Postgres, `string` en la frontera de la API, y una librería decimal en
el cliente. Sin esta regla, el consumo de presupuesto de un agente deriva por centavos al mes y
el corte duro del 100% se dispara tarde o temprano por la razón equivocada.

**8.4 Concurrencia.** El borrador proponía *"optimistic lock por `trace_id` + estado
esperado"*. Con un registro append-only hay una primitiva mejor y más barata: la **restricción
`unique (trace_id, seq)`** de §6. Quien aprueba lee el caso con `ultimo_seq = N` e inserta el
evento con `seq = N+1`; si dos personas aprueban el mismo HITL a la vez, la segunda inserción
viola la restricción y la transacción entera se revierte. No hay estado que comparar ni candado
que liberar, y la segunda persona ve *"este caso ya lo resolvió Nay hace un momento"* en vez de
sobrescribirla.

**8.5 Presupuesto (`services/budget/control.py`).** El puerto más simple: lee `budget.yaml`
desde git, agrega el consumo desde `eventos`, compara. Alerta al 80%, corte duro al 100%. Los
servicios `svc-*` se excluyen del panorama porque cuestan cero.

## 9. La siembra inicial

`scripts/migrar_a_postgres.py`, por escribir. Idempotente, igual que
`scripts/migrar_bitacora.py`, y con la misma disciplina: **conserva la fecha y el trace
originales**. Un registro que se rellena con la fecha de la importación deja de servir para
reconstruir el pasado.

Importa, en este orden:

1. `personas` — Gabriel, Nay, Ana, Elias, más contador y abogado. Sin `clerk_user_id` todavía:
   se vincula cuando cada quien acepte su invitación.
2. Los 42 eventos de `data/runlog/runlog.jsonl` → `eventos`, con `seq` asignado por orden de
   aparición dentro de cada trace.
3. Plegado de `eventos` → `casos` (12 casos).
4. Los 12 YAML de `office/encargos/` → `encargos`, enlazados a su `trace_id`.
5. Las notas de `agents/memoria/*.md` → `memoria_notas`.
6. El historial de `office/pausa.yaml` → `pausa` (una fila, ya cerrada: `hasta` poblado).

**Criterio de aceptación de la migración, verificable:** `python -m office.cli estado` leyendo
Postgres produce **byte por byte** la misma salida que hoy leyendo archivos. Se captura la
salida actual antes de migrar y se compara con `diff`. Si difiere, la migración está mal, y se
sabe antes de que alguien dependa de ella.

## 10. Vistas

| # | Vista | Fase | Notas |
|---|---|---|---|
| 1 | Login | A | Clerk. Autenticado sin fila en `personas` no entra (§7.4) |
| 2 | Resumen | A | Agentes por estado, HITL abiertos con el SLA más próximo a vencer, salud del registro, consumo del periodo |
| 3 | Agentes | A | Los 8 declarados + los 9 consultores. Detalle: misión, herramientas, límites, **condiciones de encendido con su responsable**, memoria reciente, prompt |
| 4 | Bandeja de HITL | B | Ordenable por SLA restante. Aprobar/Rechazar sólo para quien tiene autoridad (§7). **Bloqueada para D4-03 hasta resolver §7.2** |
| 5 | Presupuesto | C | Consumo vs. tope por agente. Ver §14.2: hoy sale en ceros |
| 6 | Casos | A | Buscador de `trace_id`: estado, tiempo por paso, reintentos, escalamientos, historia completa |
| 7 | Salud del registro | A | **todas las reglas, 4 estados** (§2.1), con el commit y la fecha de la última corrida de CI |
| 8 | Convocar agente | B | Envuelve las reglas de `agents/runtime.py:convocar()`: pausa activa, `listo`/`planned`, `invocable_por` |
| 9 | Pausa de la oficina | B | Sólo Gabriel. Exige motivo **y** condición de reanudación: la fila no se puede insertar sin ambos (§6) |
| 10 | Oficina (pixel art) | C | La vista actual, embebida. No se reemplaza |

La vista 3 merece una nota: mostrar las condiciones de encendido con su responsable convierte
el registro en una lista de pendientes con dueño. Es lo que hace visible que el propio portal
es la condición que falta en cinco agentes (§1).

## 11. Salud del registro por CI

Se crea `.github/workflows/validar.yml`. En cada push y cada PR:

1. `python -m pytest` — la suite completa.
2. `python scripts/validate_registry.py --verbose`.
3. Escribe el resultado de ambos a `validacion_registro` (§6), con `commit_sha` y `rama`.

El portal lee la última fila de la rama `main`. Cero duplicación de las reglas, cero deriva
posible, y el repositorio gana la CI que hoy no tiene (§2.4). El costo aceptado: la vista
muestra el estado **del último commit validado**, no del instante. La vista lo dice con la
fecha y el SHA a la vista, en vez de fingir que es en vivo.

La CI se construye **antes** de la Fase A. Un portal que reporta la salud del registro
apoyándose en una CI que no existe reporta su propia ausencia de datos como si fuera salud.

## 12. Seguridad

- **Una sola ruta de escritura.** Todo `INSERT` pasa por un route handler server-side que
  valida rol y regla de negocio antes de tocar la base. Ningún chequeo del cliente cuenta.
- **Autor real en cada evento.** `eventos.autor_persona` es una FK a `personas`, poblada desde
  la sesión de Clerk. No es un flag de texto libre como el `--autor` del CLI.
- **`eventos` sin UPDATE ni DELETE.** El rol de aplicación recibe `INSERT` y `SELECT` sobre esa
  tabla, nada más. Append-only impuesto por permisos, no por disciplina.
- **Postgres administrado** (Supabase): durabilidad y respaldo por defecto. Resuelve de raíz el
  riesgo de perder información en un filesystem efímero.
- **Concurrencia** por `unique (trace_id, seq)` (§8.4).
- **Protección de despliegue de Vercel** activada, para que los previews de cada PR no queden
  públicos. Un preview abierto es el portal entero sin Clerk delante.

## 13. Verificación

Criterios de `E-008`, en orden de ejecución:

1. **Antes de tocar nada:** `python -m pytest` y `validate_registry.py` en verde. Se guarda la
   salida de `office.cli estado` como línea base.
2. **Migración:** `diff` entre la línea base y `office.cli estado` leyendo Postgres. Idéntico o
   la migración se rehace (§9).
3. **Puerto del SLA:** el test de TypeScript contra `tests/fixtures/sla-vectores.json` en
   verde, los 17 vectores.
4. **Fase A:** login, y los datos de las vistas de lectura cuadran con `office.cli estado` y
   `validate_registry.py --verbose` corridos en paralelo.
5. **Fase B:** dos navegadores con personas distintas. Una intenta aprobar un HITL fuera de su
   equipo → se rechaza. La otra dentro del suyo → pasa y queda registrado con su nombre. Las
   dos aprueban el mismo HITL a la vez → una gana, la otra ve el mensaje de §8.4, y el registro
   tiene **un** evento, no dos.
6. **Antes de cada fase:** `pytest` y `validate_registry.py` otra vez, para confirmar que nada
   de esto tocó el sistema existente.

## 14. Lo que este plan declara de sí mismo

Cinco cosas, porque un plan que se presenta más resuelto de lo que está da permiso para no
mirar.

**14.1 — La contradicción de §7.2 no está resuelta.** Bloquea la aprobación de HITL de D4-03 en
la Fase B. La cierra Dirección eligiendo una de tres opciones en un YAML, no yo escribiendo
código.

**14.2 — La vista de presupuesto va a salir en ceros.** Los cinco agentes están `listo, sin
encender`; `svc-runlog` no tiene un solo paso con `tokens > 0`. La vista es correcta y estará
vacía hasta el primer agente encendido — y como el encendido depende de este portal, el orden
es forzoso. Por eso está en la Fase C.

**14.3 — Los topes de `budget.yaml` no están calibrados.** El propio archivo lo dice:
`calibrado: false`, *"un punto de partida derivado del nivel de modelo, no de consumo
observado"*. El portal va a pintar porcentajes contra un tope inventado. Debe mostrar el
`calibrado: false` en la pantalla, no esconderlo detrás de una barra de progreso que parece
autoridad.

**14.4 — Los festivos siguen sin cargar.** Ya no es un defecto del código: el mecanismo
existe, está probado (`test_un_festivo_no_cuenta_para_el_reloj`) y un día listado en
`calendario-laboral.yaml → festivos.fechas` se salta igual que un sábado. Lo que falta es
**el dato**, y la lista está vacía a propósito.

No se rellena a ojo. Los días del artículo 74 de la LFT son públicos, pero cuáles descansa
Fleeter de verdad —y si para operación o sólo administración— es un dato de la empresa que
nadie ha confirmado. Una lista inventada sería peor que ninguna: el sistema se vería
calibrado. Mientras tanto, un HITL de criticidad alta abierto el 15 de septiembre por la
tarde vence el 16, que es feriado. El archivo lo declara con `calibrado: false`,
`responsable: Nay`, `decide: Gabriel`, y el portal debe mostrarlo, no disimularlo.

**14.5 — El portal no puede registrarse como `svc-*`.** Sería lo natural dado cómo funciona
este repositorio, y no se puede: la regla `7c` exige que todo servicio `built` tenga módulo
Python, y esto es TypeScript. Registrarlo rompería el validador que la vista 7 muestra. El
portal pertenece a la capa `office/`, no a `services/`, y no entra al registro.

Ninguna de las cinco se cierra escribiendo código. Se cierran confirmando un YAML, calibrando
un umbral o encendiendo un agente.

## 15. Lo que necesito de ti

No puedo crear cuentas ni gastar dinero en tu nombre:

- Proyecto en **Vercel**, conectado a este repo, root directory `web/`.
- Proyecto en **Supabase** (o Postgres administrado equivalente) y su `DATABASE_URL`.
- Aplicación en **Clerk** en modo restringido/invite-only, y sus claves.

Y una decisión que no es técnica: **la de §7.2**, sobre si Ana aprueba o no los HITL de
pricing. Sin ella la Fase B queda a medias.

Lo que sí puedo hacer sin nada de eso, y es lo que sigue si lo apruebas: la CI (§11), el script
de migración (§9) y la app completa contra un Postgres local y un Clerk en modo test.

## 16. Fases

| | Qué | Depende de |
|---|---|---|
| **0** | ~~CI (§11)~~ ✅ · ~~puerto del SLA (§8.1)~~ ✅ · ~~calendario y SLA configurables~~ ✅ · falta `migrar_a_postgres.py` (§9) | Lo que falta depende de que exista la base de datos |
| **A** | Esqueleto + sólo lectura. Vistas 1, 2, 3, 6, 7 | Fase 0, y las tres cuentas |
| **B** | Acciones: aprobar/rechazar HITL, convocar, pausar. Vistas 4, 8, 9 | Fase A + **la decisión de §7.2** |
| **B+** | Cerrar `cumplida: true` en la condición de bandeja de HITL de los cinco agentes | Fase B verificada en producción |
| **C** | Presupuesto (vista 5), pixel art embebido (vista 10), diseño final | Fase B. La vista 5 sólo tiene datos después de encender el primer agente |

La fila **B+** es el punto del ejercicio. Todo lo demás es infraestructura para llegar ahí.

## 17. Ciclo de vida de un agente `[CONSTRUIDO]`

Un organigrama que sólo sabe crecer no es un organigrama: es una lista que nadie poda. Los
cuatro estados y las dos formas de detener a un agente existen porque son preguntas
distintas.

| Estado | Qué significa | Dónde vive | Cómo se cambia |
|---|---|---|---|
| `planned` | Declarado en el roadmap; todavía no existe | `registry/agents/*.yaml` | PR |
| `listo` | Contrato completo, con condiciones de encendido pendientes | idem | PR + regla 13 |
| `built` | Encendido; se puede convocar | idem | PR, tras cumplir sus condiciones |
| `retirado` | Dado de baja; su historia sigue consultable | idem | PR + **regla 14** |

**Pausar no es retirar, y por eso no viven en el mismo sitio.** Pausar es operativo y
reversible: se escribe en Postgres (`agente_pausa`), con motivo y condición de reanudación
obligatorios, y se hace desde el portal en dos clics. Retirar es contractual y definitivo:
se escribe en el YAML, pasa por PR y queda en el historial de git. Un agente pausado sigue
siendo `built` — simplemente hoy no trabaja.

**Un agente retirado nunca se borra.** Borrarlo dejaría huérfanos sus encargos, su memoria y
cada `trace_id` donde aparece como actor, y la pregunta *"¿quién decidió esto en marzo?"*
dejaría de tener respuesta. La **regla 14** exige que el retiro declare fecha, responsable,
motivo y **quién cubre ese trabajo ahora** — y falla si un equipo se queda sin agente digital
vivo sin decir quién lo sustituye.

### Dar de alta un agente

Toca cinco archivos, y el orden importa. `scripts/nuevo_agente.py` los escribe todos y
después corre el validador:

```bash
python scripts/nuevo_agente.py --id D3-01 --nombre "Planeación de Rutas"     --departamento 03-operaciones --equipo T03-01 --fase 5     --persona Lucía --mision "Arma la programación semanal sobre capacidad real."
```

| # | Archivo | Por qué |
|---|---|---|
| 1 | `registry/policies/roadmap.yaml` | El roadmap manda: *"un ID que no esté aquí no puede aparecer en ningún registro"* |
| 2 | `registry/agents/<ID>-<slug>.yaml` | El contrato |
| 3 | `registry/teams/<EQUIPO>.yaml` | Sin equipo no hay owner humano, y sin owner humano su HITL no tiene a dónde llegar |
| 4 | `office/identidades.yaml` | Nombre, voz y un escritorio libre en el plano |
| 5 | `agents/memoria/<ID>.md` | Su memoria, vacía pero existente |

El agente nace `planned`: existe y no se puede convocar. Subirlo a `listo` exige escribir sus
condiciones de encendido. El estado no se sube a mano sin cerrar lo que el estado promete.

`--dry-run` dice qué haría sin tocar nada.

### Lo que se arregló para que esto funcione

`tests/unit/test_office.py` fijaba el número de agentes en duro (`== 17`). Dar de alta un
agente rompía la suite — lo contrario de un sistema que crece. Ahora las cifras se **derivan
del registro**: la prueba afirma que el plano dibuja exactamente a quien tiene identidad, no
que sean diecisiete. La relación es la invariante; el número es una consecuencia.
