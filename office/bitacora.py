"""Bitacora de la oficina: hoy es una vista de `svc-runlog`, no un registro aparte.

Hasta la Fase 1 esto era un JSONL propio, precursor declarado del servicio. Ya no: los
eventos de la oficina —convocatorias, inicios, bloqueos, notas— se escriben en el mismo
registro que los casos de negocio, con el mismo `trace_id` y la misma maquina de estados.

Por que importa que sean uno solo: con dos registros, "¿cuanto costo este caso?" y "¿quien
lo trabajo?" se responden en archivos distintos y nadie garantiza que cuadren. Un agente
que arranca en la oficina y termina cotizando deja un solo rastro, o no deja ninguno util.

    evento de oficina        lo que queda en svc-runlog
    ---------------------    ------------------------------------------------------
    convocatoria             apertura del caso (tipo: encargo)
    inicio                   transicion recibido -> en_proceso
    bloqueo / desbloqueo     transicion a bloqueado y de vuelta a en_proceso
    entrega                  transicion en_proceso -> esperando_validacion
    cierre                   camino hasta entregado (por el humano si el encargo es HITL)
    nota / evaluacion        paso, sin mover el estado

Cada evento deja ademas un `paso` que carga los campos de la oficina (agente, encargo,
autor, detalle). Ese paso es lo que `leer()` devuelve: la vista de oficina del registro.

El archivo viejo, `office/bitacora.jsonl`, no se reescribe ni se borra. Se importo con
`scripts/migrar_bitacora.py` y se queda como estaba, que es lo que corresponde a un
registro append-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from services.runlog.caso import (
    BLOQUEADO,
    ENTREGADO,
    ESPERANDO_HUMANO,
    ESPERANDO_VALIDACION,
    EN_PROCESO,
    RECIBIDO,
    TRANSICIONES,
    ahora,
)
from services.runlog.registro import RunLog

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "data" / "runlog" / "runlog.jsonl"

# El JSONL de la oficina antes de la migracion. Se conserva como historico.
HISTORICO = RAIZ / "office" / "bitacora.jsonl"

EVENTOS = (
    "convocatoria",   # se le encarga algo a un agente
    "inicio",         # el agente empieza a trabajar
    "entrega",        # el agente entrega
    "bloqueo",        # el caso se detiene: falta contexto o falta una aprobacion humana
    "desbloqueo",
    "cierre",
    "nota",           # el agente anota en su memoria
    "evaluacion",     # D5-03 revisa calidad
    "pausa",          # la oficina se detiene por decision escrita
    "reanudacion",
)

# Tipo de paso de §8.1 con el que se escribe cada evento de oficina.
TIPO_DE_PASO = {
    "convocatoria": "ruteo",
    "inicio": "accion",
    "entrega": "entrega",
    "bloqueo": "accion",
    "desbloqueo": "accion",
    "cierre": "entrega",
    "nota": "accion",
    "evaluacion": "validacion",
    "pausa": "accion",
    "reanudacion": "accion",
}

# A donde tiene que quedar el caso despues del evento. Los eventos que no aparecen aqui
# no mueven el estado: una nota no cambia en que va el encargo.
DESTINO = {
    "inicio": EN_PROCESO,
    "bloqueo": BLOQUEADO,
    "desbloqueo": EN_PROCESO,
    "entrega": ESPERANDO_VALIDACION,
    "cierre": ENTREGADO,
}


@dataclass(frozen=True)
class Entrada:
    ts: str
    trace_id: str
    evento: str
    agente: str
    encargo: str
    detalle: str
    autor: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _registro() -> RunLog:
    # Se instancia por llamada, no una vez: asi redirigir ARCHIVO en las pruebas basta.
    return RunLog(ARCHIVO)


def _tipo_de_caso(evento: str, encargo: str) -> str:
    if evento == "convocatoria":
        return "encargo"
    if encargo and encargo != "-":
        return "nota"
    return "oficina"


def _camino(desde: str, hasta: str, *, hitl: bool) -> list[str]:
    """Los estados intermedios que hay que atravesar, en orden, para llegar a `hasta`.

    La oficina tiene cuatro estados y `svc-runlog` ocho: `hecho` no es una transicion, es un
    camino. El mas corto se calcula sobre la misma maquina de estados del servicio, para que
    la oficina no pueda inventarse un atajo que el registro no permite — por ejemplo cerrar
    un encargo sin pasar por validacion.
    """
    if desde == hasta:
        return []

    preferido = ESPERANDO_HUMANO if hitl else ESPERANDO_VALIDACION
    visitados = {desde}
    frontera: list[tuple[str, list[str]]] = [(desde, [])]
    while frontera:
        actual, ruta = frontera.pop(0)
        vecinos = sorted(TRANSICIONES[actual], key=lambda e: (e != preferido, e))
        for vecino in vecinos:
            if vecino == hasta:
                return ruta + [vecino]
            if vecino not in visitados:
                visitados.add(vecino)
                frontera.append((vecino, ruta + [vecino]))
    raise ValueError(f"no hay camino de {desde} a {hasta} en la maquina de estados del caso")


def leer(limite: int | None = None) -> list[Entrada]:
    """Los eventos de oficina del registro, en orden. Los pasos de negocio no salen aqui."""
    registro = _registro()
    entradas: list[Entrada] = []
    for evento in registro._eventos():  # noqa: SLF001 - misma casa, mismo archivo
        if evento.get("evento") != "paso":
            continue
        oficina = evento.get("entradas") or {}
        if "evento_oficina" not in oficina:
            continue
        entradas.append(
            Entrada(
                ts=evento["ts"],
                trace_id=evento["trace_id"],
                evento=oficina["evento_oficina"],
                agente=evento["actor"],
                encargo=oficina.get("encargo", "-"),
                detalle=oficina.get("detalle", ""),
                autor=oficina.get("autor", "sistema"),
            )
        )
    return entradas[-limite:] if limite else entradas


def nuevo_trace(prefijo: str = "TR") -> str:
    """Un trace por convocatoria, legible y ordenable: TR-20260818-003."""
    return _registro().nuevo_trace(prefijo)


def registrar(
    *,
    evento: str,
    agente: str,
    encargo: str = "-",
    detalle: str = "",
    autor: str = "sistema",
    trace_id: str | None = None,
    hitl: bool = False,
    criticidad: str = "media",
    ts: str | None = None,
) -> Entrada:
    """Escribe el evento en `svc-runlog` y devuelve como se ve desde la oficina.

    `ts` sólo lo usa la importacion del historico; en operacion normal la fecha la pone el
    registro.
    """
    if evento not in EVENTOS:
        raise ValueError(f"evento desconocido: {evento!r}; validos: {', '.join(EVENTOS)}")

    registro = _registro()
    momento = ts or ahora().isoformat(timespec="seconds")
    identificador = trace_id or registro.nuevo_trace()

    if identificador not in registro.casos():
        registro.abrir_caso(
            tipo=_tipo_de_caso(evento, encargo),
            referencia=encargo if encargo and encargo != "-" else agente,
            criticidad=criticidad,
            actor=agente,
            trace_id=identificador,
            ts=momento,
        )

    detalle_limpio = " ".join(detalle.split())

    destino = DESTINO.get(evento)
    if destino:
        estado = registro.caso(identificador).estado
        for intermedio in _camino(estado, destino, hitl=hitl):
            registro.transicionar(
                identificador,
                intermedio,
                actor=autor,
                motivo=detalle_limpio or f"oficina: {evento}",
                ts=momento,
            )

    registro.registrar_paso(
        identificador,
        actor=agente,
        tipo=TIPO_DE_PASO[evento],
        entradas={
            "evento_oficina": evento,
            "encargo": encargo,
            "autor": autor,
            "detalle": detalle_limpio,
        },
        ts=momento,
    )

    return Entrada(
        ts=momento,
        trace_id=identificador,
        evento=evento,
        agente=agente,
        encargo=encargo,
        detalle=detalle_limpio,
        autor=autor,
    )


def trace_de(encargo_id: str) -> list[Entrada]:
    """Todo lo que le paso a un encargo, en orden. Es la respuesta a '¿en que va esto?'."""
    return [e for e in leer() if e.encargo == encargo_id]


def progreso_de(trace_id: str):
    """El progreso del caso segun `svc-runlog`: estado, responsable y siguiente paso.

    Es lo que la oficina gana con la migracion: antes tenia una lista de eventos y habia que
    interpretarla; ahora pregunta y le contestan, sin invocar a ningun modelo (§8.2).
    """
    return _registro().progreso(trace_id)


__all__ = [
    "ARCHIVO",
    "EVENTOS",
    "Entrada",
    "HISTORICO",
    "leer",
    "nuevo_trace",
    "progreso_de",
    "registrar",
    "trace_de",
]
