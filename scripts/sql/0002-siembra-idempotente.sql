-- 0002 — Lo que la siembra descubrió que faltaba en el esquema de docs/portal.md §6.
--
-- El esquema original (0001) se escribió antes de mirar los datos que iba a recibir. Al
-- escribir scripts/migrar_a_postgres.py aparecieron tres huecos, y los tres son del mismo
-- tipo: el esquema no podía representar un hecho que los archivos ya afirman, o no podía
-- correrse dos veces sin duplicar.
--
-- Se corrige el esquema, no el dato. Ajustar los datos para que quepan en una tabla es
-- exactamente cómo un sistema empieza a mentir.

begin;

-- --------------------------------------------------------------------------
-- 1. Un encargo lo puede convocar un agente, no sólo una persona.
--
-- §6 declaró `convocado_por uuid not null references personas(id)`. Pero nueve de los doce
-- encargos de office/encargos/ dicen `convocado_por: D5-01` — el Jefe de Gabinete, que es un
-- agente. La FK obligatoria sólo se podía satisfacer inventando: metiendo a D5-01 en
-- `personas` (un agente no es una persona, y `personas` es el puente con Clerk), o poniendo
-- ahí al owner humano de su equipo (atribuirle a Gabriel una convocatoria que no hizo).
--
-- La forma honesta es guardar lo que el YAML dice y decir cuándo eso es una persona.
-- --------------------------------------------------------------------------

alter table encargos alter column convocado_por drop not null;

alter table encargos add column if not exists convocado_por_actor text not null default '';

comment on column encargos.convocado_por_actor is
  'Quien convocó, literal: puede ser una persona (Gabriel) o un agente (D5-01).';

comment on column encargos.convocado_por is
  'La persona que convocó, cuando fue una persona. Null si fue un agente; el nombre del '
  'agente está en convocado_por_actor. No se rellena con el owner del equipo: eso sería '
  'atribuirle una acción que no hizo.';

-- Un actor siempre hay. Lo que puede faltar es la persona.
alter table encargos drop constraint if exists encargos_actor_declarado;
alter table encargos add constraint encargos_actor_declarado
  check (convocado_por_actor <> '');

-- --------------------------------------------------------------------------
-- 2 y 3. Claves naturales para que la siembra sea idempotente.
--
-- `memoria_notas` y `pausa` se declararon con `bigserial` y ninguna restricción más. Una
-- tabla sin clave natural no se puede sembrar dos veces: la segunda corrida duplica todo, y
-- entonces la migración deja de ser reejecutable — que es justo lo que §9 exige de ella.
--
-- La clave no se inventa: es lo que de verdad identifica a cada fila en su archivo de origen.
-- --------------------------------------------------------------------------

-- Una nota es única por quién la escribió, cuándo, sobre qué encargo, de qué tipo y qué dice.
-- Se indexa md5(texto) y no el texto: una nota larga desbordaría el límite de tamaño de una
-- entrada de índice btree, y ese fallo aparecería el día que alguien escriba una nota larga.
create unique index if not exists memoria_notas_sin_duplicados
  on memoria_notas (agente, fecha, encargo, tipo, md5(texto));

-- No puede haber dos pausas que empiecen en el mismo instante. `pausa_activa_unica` (0001)
-- ya impedía dos pausas abiertas a la vez; esto impide reimportar el historial.
create unique index if not exists pausa_desde_unica on pausa (desde);

commit;
