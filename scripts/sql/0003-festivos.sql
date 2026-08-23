-- 0003 — Los festivos, que dejan de ser una lista en YAML y pasan a ser operación.
--
-- POR QUÉ SE MUEVEN. §3 dice que las políticas viven en git, y sigue siendo verdad para el
-- huso, la jornada y los días hábiles: son mecanismo, cambian casi nunca y un umbral que se
-- edita desde una pantalla es un umbral sin auditoría.
--
-- Los festivos no son eso. Son un **catálogo de datos de la empresa** que cambia cada año,
-- que nadie va a mantener por PR, y que lleva vacío desde que existe el calendario —con
-- consecuencia real: hoy un HITL de criticidad alta abierto el 15 de septiembre por la tarde
-- vence el 16, que es feriado, y no hay nadie para atenderlo. Una lista que sólo se puede
-- llenar abriendo un pull request es una lista que se queda vacía.
--
-- LO QUE NO SE PIERDE AL MOVERLOS. La auditoría, que era la razón de tenerlos en git: cada
-- fila dice quién la declaró, cuándo y de dónde salió. Eso es más de lo que daba el YAML,
-- donde `git blame` decía quién editó el archivo pero no de dónde vino el dato.
--
-- LO QUE NO SE HACE. Rellenarlos por nadie. Los días del artículo 74 de la LFT son públicos,
-- pero cuáles descansa Fleeter de verdad —y si para operación o sólo administración— es un
-- dato de la empresa que nadie ha confirmado. La tabla nace vacía, a propósito.

begin;

create table if not exists festivos (
  fecha          date primary key,
  motivo         text not null check (length(trim(motivo)) > 0),

  -- De dónde salió. Importa para saber qué se puede volver a importar sin pisar lo que
  -- alguien escribió a mano.
  --   manual   lo capturó una persona en el portal
  --   ics      vino de un archivo .ics exportado de un calendario
  --   yaml     se sembró desde registry/policies/calendario-laboral.yaml
  origen         text not null default 'manual'
                 check (origen in ('manual', 'ics', 'yaml')),

  -- Qué para. Un feriado que para administración pero no operación no es el mismo hecho, y
  -- el día que Fleeter lo distinga, el dato ya está separado.
  --   completo        no se trabaja
  --   administrativo  para administración; operación sigue
  alcance        text not null default 'completo'
                 check (alcance in ('completo', 'administrativo')),

  -- Quién responde por este dato. Es lo que el YAML no podía dar.
  declarado_por  uuid references personas(id),
  creado_en      timestamptz not null default now(),

  -- El identificador del evento en el calendario de origen, cuando vino de un .ics. Permite
  -- reimportar el mismo archivo sin duplicar ni pisar ediciones manuales.
  uid_externo    text
);

comment on table festivos is
  'Días que no cuentan para el reloj del SLA, igual que un sábado. Los leen services/runlog/sla.py y web/lib/reglas/sla.ts: una sola fuente para las dos implementaciones.';

comment on column festivos.alcance is
  'completo = no se trabaja. administrativo = para administración, operación sigue.';

-- Reimportar un .ics no puede duplicar. El uid del evento es su clave natural cuando existe.
create unique index if not exists festivos_uid_externo_unico
  on festivos (uid_externo) where uid_externo is not null;

create index if not exists festivos_por_anio on festivos ((extract(year from fecha)));

commit;
