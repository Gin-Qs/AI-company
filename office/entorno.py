"""Que comandos de escritura del CLI siguen permitidos, y donde (docs/portal.md §4).

EL PROBLEMA QUE ESTO CIERRA. Despues del portal, **Postgres es la verdad operativa**. Pero
`office.cli convocar` sigue sabiendo escribir un YAML en `office/encargos/` y un evento en
`data/runlog/runlog.jsonl`. Si alguien lo corre contra el sistema en produccion, el encargo
existe en los archivos y NO en la base: el portal no lo ve, el `trace_id` no cuadra con nada,
y la pregunta "¿cuantos encargos hay abiertos?" tiene dos respuestas.

No es hipotetico. Hoy `office/encargos/` tiene doce YAML y Postgres tiene doce filas, y
coinciden **solo porque nadie ha creado uno nuevo desde ninguno de los dos lados**. El primero
que se cree por el lado equivocado abre la brecha, y a partir de ahi nadie sabe cual mirar.

LA REGLA. Los comandos que escriben estado operativo —`convocar`, `avanzar`, `recordar`—
exigen `AI_COMPANY_ENTORNO=local` y fallan en cualquier otro caso. Los de lectura —`estado`,
`build`— no se tocan: leen, y `estado` ya lee la pausa de Postgres.

POR QUE UNA VARIABLE Y NO DETECTAR LA BASE. Se considero prohibirlos "cuando haya DATABASE_URL
configurada", y es peor: quien programa tiene la base configurada en su maquina para poder
correr las pruebas, y se quedaria sin poder usar el CLI. Y al reves, olvidar exportar la
variable en un servidor volveria a abrir la puerta. Una declaracion explicita de intencion
—"esto es mi maquina de desarrollo"— no se activa por accidente en ninguno de los dos lados.

`services.cli` NO pasa por aqui. Sus cinco comandos son calculo puro sobre `data/ejemplo`: no
escriben estado operativo y no tienen por que cambiar.
"""

from __future__ import annotations

import os

VARIABLE = "AI_COMPANY_ENTORNO"
LOCAL = "local"


class EscrituraFueraDeLocal(RuntimeError):
    """Se intento escribir estado operativo desde el CLI sin declarar entorno local."""


def es_local() -> bool:
    return os.environ.get(VARIABLE, "").strip().lower() == LOCAL


def exigir_local(comando: str) -> None:
    """Deja pasar solo en desarrollo. En cualquier otro caso, explica que hacer en su lugar.

    El mensaje nombra el comando y la alternativa a proposito: un error que solo dice "no
    permitido" manda a la persona a buscar como saltarselo, y saltarselo es justo lo que crea
    la segunda verdad.
    """
    if es_local():
        return
    raise EscrituraFueraDeLocal(
        f"`office.cli {comando}` escribe en archivos, y desde el portal la verdad operativa "
        f"vive en Postgres (docs/portal.md §4). Correrlo aqui crearia un encargo que el "
        f"portal no ve.\n\n"
        f"  Si querias hacerlo de verdad: hazlo en el portal.\n"
        f"  Si estas desarrollando en tu maquina: export {VARIABLE}={LOCAL}\n\n"
        f"Los comandos de lectura (`estado`, `build`) no necesitan nada de esto."
    )
