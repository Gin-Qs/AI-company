"""svc-runlog - el registro del camino y el progreso de cada caso (§8).

Append-only e inmutable. Los casos no se guardan como filas que se actualizan: se
reconstruyen plegando los eventos, de modo que el estado de ayer siempre se puede volver a
calcular. Esa es la diferencia entre un registro y una tabla de estado.

    svc-trace  = trazabilidad de cifras   ("¿de donde salio este numero?")
    svc-runlog = trazabilidad de proceso  ("¿por donde paso el caso y en que va?")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from services.common.errors import ErrorDeIntegridad, ErrorDeValidacion
from services.common.money import mxn
from services.runlog.caso import (
    BLOQUEADO,
    CRITICIDADES,
    EN_PROCESO,
    ESPERANDO_HUMANO,
    ENTREGADO,
    RECHAZADO_VALIDACION,
    Caso,
    Paso,
    Transicion,
    ahora,
)
from services.runlog.sla import Vencimiento, resolver_vencimiento, vencimiento

RAIZ = Path(__file__).resolve().parent.parent.parent
ARCHIVO_POR_DEFECTO = RAIZ / "data" / "runlog" / "runlog.jsonl"


@dataclass(frozen=True)
class Progreso:
    """La respuesta a '¿en que va la cotizacion de X?', sin invocar un LLM (§8.2)."""

    trace_id: str
    tipo: str
    referencia: str
    estado: str
    responsable: str
    desde: str
    minutos_en_estado: int
    siguiente_paso: str
    vence_en: str | None
    reintentos: int

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "tipo": self.tipo,
            "referencia": self.referencia,
            "estado": self.estado,
            "responsable": self.responsable,
            "desde": self.desde,
            "minutos_en_estado": self.minutos_en_estado,
            "siguiente_paso": self.siguiente_paso,
            "vence_en": self.vence_en,
            "reintentos": self.reintentos,
        }


SIGUIENTE_PASO = {
    "recibido": "arrancar el caso",
    "en_proceso": "producir el entregable y mandarlo a validacion",
    "esperando_validacion": "svc-validation dictamina",
    "rechazado_validacion": "corregir y reintentar",
    "esperando_humano": "espera aprobacion en la bandeja de HITL",
    "entregado": "nada, el caso cerro",
    "bloqueado": "lo resuelve una persona",
    "expirado": "nada, expiro sin atenderse",
}


class RunLog:
    """Un registro. Se instancia con su archivo para poder aislarlo en pruebas."""

    def __init__(self, archivo: str | Path | None = None) -> None:
        self.archivo = Path(archivo) if archivo else ARCHIVO_POR_DEFECTO

    # --- escritura ------------------------------------------------------

    def _escribir(self, evento: dict) -> None:
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        with self.archivo.open("a", encoding="utf-8") as destino:
            destino.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def _eventos(self) -> list[dict]:
        if not self.archivo.is_file():
            return []
        return [json.loads(linea) for linea in self.archivo.read_text(encoding="utf-8").splitlines() if linea.strip()]

    def abrir_caso(
        self,
        *,
        tipo: str,
        referencia: str,
        criticidad: str = "media",
        actor: str = "O1",
        trace_id: str | None = None,
        ts: str | None = None,
    ) -> Caso:
        """Abre el trace del caso. Todo paso posterior lo hereda (§8.1).

        `ts` sólo se pasa al importar historia (scripts/migrar_bitacora.py). Un registro que
        se rellena con la fecha de la importación deja de servir para reconstruir el pasado.
        """
        if criticidad not in CRITICIDADES:
            raise ErrorDeValidacion(f"criticidad desconocida: {criticidad!r}", campo="criticidad")

        identificador = trace_id or self.nuevo_trace()
        if identificador in self.casos():
            raise ErrorDeIntegridad(f"el trace {identificador} ya existe", campo="trace_id")

        momento = ts or ahora().isoformat(timespec="seconds")
        self._escribir(
            {
                "evento": "apertura",
                "trace_id": identificador,
                "tipo": tipo,
                "referencia": referencia,
                "criticidad": criticidad,
                "ts": momento,
                "actor": actor,
            }
        )
        return self.caso(identificador)

    def nuevo_trace(self, prefijo: str = "TR") -> str:
        hoy = ahora().strftime("%Y%m%d")
        del_dia = {e["trace_id"] for e in self._eventos() if str(e.get("trace_id", "")).startswith(f"{prefijo}-{hoy}")}
        return f"{prefijo}-{hoy}-{len(del_dia) + 1:03d}"

    def registrar_paso(
        self,
        trace_id: str,
        *,
        actor: str,
        tipo: str,
        resultado: str = "ok",
        parent_span_id: str | None = None,
        decision_ruteo: str = "",
        entradas: dict[str, str] | None = None,
        salidas: dict[str, str] | None = None,
        versiones: dict[str, str] | None = None,
        tokens: int = 0,
        costo_mxn: object = 0,
        latencia_ms: int = 0,
        gate: dict[str, str] | None = None,
        ts: str | None = None,
    ) -> Paso:
        """Registra un paso del caso. Los reintentos se registran siempre (§8.1)."""
        caso = self.caso(trace_id)
        paso = Paso(
            trace_id=trace_id,
            span_id=f"{trace_id}.{caso.pasos + 1:03d}",
            parent_span_id=parent_span_id,
            actor=actor,
            tipo=tipo,
            ts=ts or ahora().isoformat(timespec="seconds"),
            resultado=resultado,
            decision_ruteo=decision_ruteo,
            entradas=entradas or {},
            salidas=salidas or {},
            versiones=versiones or {},
            tokens=tokens,
            costo_mxn=mxn(costo_mxn),
            latencia_ms=latencia_ms,
            gate=gate or {},
        )
        self._escribir(paso.as_dict())
        return paso

    def transicionar(
        self, trace_id: str, destino: str, *, actor: str, motivo: str = "", ts: str | None = None
    ) -> Caso:
        """Mueve el caso, validando la maquina de estados y el limite de reintentos."""
        caso = self.caso(trace_id)
        caso.exigir_transicion(destino)

        transicion = Transicion(
            trace_id=trace_id,
            de=caso.estado,
            a=destino,
            ts=ts or ahora().isoformat(timespec="seconds"),
            actor=actor,
            motivo=motivo,
        )
        self._escribir(transicion.as_dict())
        return self.caso(trace_id)

    # --- lectura --------------------------------------------------------

    def casos(self) -> dict[str, Caso]:
        """Pliega el registro y devuelve el estado actual de cada caso."""
        casos: dict[str, Caso] = {}
        for evento in self._eventos():
            trace_id = evento.get("trace_id")
            if evento.get("evento") == "apertura":
                casos[trace_id] = Caso(
                    trace_id=trace_id,
                    tipo=evento["tipo"],
                    referencia=evento["referencia"],
                    criticidad=evento["criticidad"],
                    abierto_en=evento["ts"],
                    actualizado_en=evento["ts"],
                    responsable=evento.get("actor", ""),
                )
                continue

            caso = casos.get(trace_id)
            if caso is None:
                raise ErrorDeIntegridad(
                    f"hay eventos del trace {trace_id} sin apertura: el registro esta incompleto",
                    campo="trace_id",
                )

            if evento.get("evento") == "paso":
                caso.pasos += 1
                caso.tokens += int(evento.get("tokens") or 0)
                caso.costo_mxn = mxn(caso.costo_mxn + mxn(evento.get("costo_mxn") or 0))
                caso.responsable = evento.get("actor", caso.responsable)
                caso.actualizado_en = evento["ts"]
            elif evento.get("evento") == "transicion":
                if evento["a"] == EN_PROCESO and evento["de"] == RECHAZADO_VALIDACION:
                    caso.reintentos += 1
                if evento.get("motivo", "").startswith("escalamiento"):
                    caso.escalamientos += 1
                caso.estado = evento["a"]
                caso.actualizado_en = evento["ts"]
                caso.responsable = evento.get("actor", caso.responsable)

        return casos

    def caso(self, trace_id: str) -> Caso:
        casos = self.casos()
        if trace_id not in casos:
            raise ErrorDeIntegridad(f"trace inexistente: {trace_id}", campo="trace_id")
        return casos[trace_id]

    def pasos(self, trace_id: str) -> list[Paso]:
        return [
            Paso.desde_dict(e) for e in self._eventos() if e.get("evento") == "paso" and e.get("trace_id") == trace_id
        ]

    def progreso(self, trace_id: str, *, momento: datetime | None = None) -> Progreso:
        """Estado, responsable, tiempo en el estado y siguiente paso. Sin LLM (§8.2)."""
        caso = self.caso(trace_id)
        ultimo = caso.actualizado_en
        referencia_tiempo = momento or ahora()
        desde = datetime.fromisoformat(ultimo)
        if desde.tzinfo is None:
            desde = desde.replace(tzinfo=timezone.utc)

        vence = None
        if caso.espera_humano:
            vence = vencimiento(desde, caso.criticidad).isoformat(timespec="seconds")

        return Progreso(
            trace_id=caso.trace_id,
            tipo=caso.tipo,
            referencia=caso.referencia,
            estado=caso.estado,
            responsable=caso.responsable,
            desde=ultimo,
            minutos_en_estado=max(int((referencia_tiempo - desde).total_seconds() // 60), 0),
            siguiente_paso=SIGUIENTE_PASO[caso.estado],
            vence_en=vence,
            reintentos=caso.reintentos,
        )

    # --- SLA ------------------------------------------------------------

    def vencidos(self, *, momento: datetime | None = None) -> list[Vencimiento]:
        """Los HITL que ya vencieron y que hacer con cada uno (§7.3). Ninguno se auto-aprueba."""
        referencia_tiempo = momento or ahora()
        pendientes: list[Vencimiento] = []
        for caso in self.casos().values():
            if not caso.espera_humano:
                continue
            desde = datetime.fromisoformat(caso.actualizado_en)
            if desde.tzinfo is None:
                desde = desde.replace(tzinfo=timezone.utc)
            resultado = resolver_vencimiento(
                trace_id=caso.trace_id,
                criticidad=caso.criticidad,
                espera_desde=desde,
                ahora=referencia_tiempo,
                escalamientos=caso.escalamientos,
            )
            if resultado:
                pendientes.append(resultado)
        return pendientes

    def aplicar_vencimiento(self, vencido: Vencimiento, *, actor: str = "svc-runlog") -> Caso:
        """Ejecuta la consecuencia del vencimiento. Escalar mantiene el caso esperando."""
        if vencido.accion == "escalar":
            self._escribir(
                {
                    "evento": "transicion",
                    "trace_id": vencido.trace_id,
                    "de": ESPERANDO_HUMANO,
                    "a": ESPERANDO_HUMANO,
                    "ts": ahora().isoformat(timespec="seconds"),
                    "actor": actor,
                    "motivo": f"escalamiento: {vencido.motivo}",
                }
            )
            return self.caso(vencido.trace_id)

        destino = BLOQUEADO if vencido.accion == "bloquear" else "expirado"
        return self.transicionar(vencido.trace_id, destino, actor=actor, motivo=vencido.motivo)

    # --- consumo (alimenta svc-budget) ----------------------------------

    def consumo(self, *, periodo: str | None = None) -> dict[str, dict[str, object]]:
        """Tokens y costo por actor, opcionalmente de un periodo `AAAA-MM`."""
        acumulado: dict[str, dict[str, object]] = {}
        for evento in self._eventos():
            if evento.get("evento") != "paso":
                continue
            if periodo and not str(evento.get("ts", "")).startswith(periodo):
                continue
            fila = acumulado.setdefault(evento["actor"], {"tokens": 0, "costo_mxn": Decimal("0.00"), "pasos": 0})
            fila["tokens"] = int(fila["tokens"]) + int(evento.get("tokens") or 0)
            fila["costo_mxn"] = mxn(Decimal(str(fila["costo_mxn"])) + mxn(evento.get("costo_mxn") or 0))
            fila["pasos"] = int(fila["pasos"]) + 1
        return acumulado

    def reintentos_por_actor(self) -> dict[str, int]:
        """Insumo de la evaluacion de D5-03: quien acierta al segundo intento y se ve perfecto."""
        conteo: dict[str, int] = {}
        for evento in self._eventos():
            if evento.get("evento") == "paso" and evento.get("resultado") == "reintento":
                conteo[evento["actor"]] = conteo.get(evento["actor"], 0) + 1
        return conteo


def entregar(runlog: RunLog, trace_id: str, *, actor: str) -> Caso:
    """Cierra el caso como entregado, registrando el paso de entrega."""
    runlog.registrar_paso(trace_id, actor=actor, tipo="entrega")
    return runlog.transicionar(trace_id, ENTREGADO, actor=actor, motivo="entregado")
