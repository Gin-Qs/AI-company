"""Genera los vectores dorados del SLA desde services/runlog/sla.py.

El portal web reimplementa este calendario en TypeScript. Una reimplementacion que
nadie contrasta contra el original diverge en silencio, y un SLA que se corre media
hora no falla: aprueba tarde y parece que funciono. Estos vectores son el contrato.

    python scripts/vectores_sla.py          # reescribe tests/fixtures/sla-vectores.json

Los momentos de entrada van en UTC a proposito: asi es como svc-runlog guarda `ts`, y
asi es como los recibe una funcion de Vercel, que corre en UTC. El calendario laboral
es hora del centro de Mexico (-6 fijo); si el puerto olvida convertir, estos vectores
lo delatan en el primer caso de viernes por la tarde.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.runlog.sla import HUSO, cargar_calendario, cargar_sla, resolver_vencimiento, vencimiento

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "tests" / "fixtures" / "sla-vectores.json"
UTC = timezone.utc


def u(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=UTC)


# (momento UTC, criticidad, por que este caso importa)
CASOS = [
    ("2026-06-02T16:00:00", "alta",  "martes 10:00 local, dentro de jornada: 4h caben el mismo dia"),
    ("2026-06-02T21:00:00", "alta",  "martes 15:00 local: las 4h cruzan el cierre y siguen el miercoles"),
    ("2026-06-05T21:30:00", "alta",  "viernes 15:30 local: cruza el fin de semana y cae el lunes"),
    ("2026-06-06T18:00:00", "alta",  "sabado: no hay jornada, el reloj arranca el lunes a las 9:00"),
    ("2026-06-02T12:00:00", "alta",  "martes 06:00 local, antes de abrir: arranca a las 9:00"),
    ("2026-06-03T02:00:00", "alta",  "martes 20:00 local, ya cerrado: arranca el miercoles"),
    ("2026-06-02T16:00:00", "media", "1 dia habil = 9h: martes 10:00 vence miercoles 10:00"),
    ("2026-06-05T16:00:00", "media", "viernes 10:00 local: 1 dia habil cae el lunes"),
    ("2026-06-02T16:00:00", "baja",  "3 dias habiles = 27h desde martes 10:00"),
    ("2026-06-04T20:00:00", "baja",  "jueves 14:00 local: 3 dias habiles cruzan el fin de semana"),
]

# (momento de espera, criticidad, escalamientos previos, cuanto despues se pregunta)
DECISIONES = [
    ("2026-06-02T16:00:00", "alta",  0, timedelta(hours=1),  "todavia no vence: no hay accion"),
    ("2026-06-02T16:00:00", "alta",  0, timedelta(days=1),   "vencio sin escalar: escala"),
    ("2026-06-02T16:00:00", "alta",  1, timedelta(days=1),   "vencio ya escalado: bloquea, nunca aprueba"),
    ("2026-06-02T16:00:00", "media", 0, timedelta(days=2),   "vencio sin escalar: escala"),
    ("2026-06-02T16:00:00", "media", 1, timedelta(days=2),   "vencio ya escalado: expira"),
    ("2026-06-02T16:00:00", "baja",  0, timedelta(days=7),   "baja expira al primer vencimiento"),
    ("2026-06-02T16:00:00", "baja",  2, timedelta(days=7),   "baja expira tambien con escalamientos"),
]


def construir() -> dict:
    cal = cargar_calendario()
    vencimientos = []
    for momento, criticidad, por_que in CASOS:
        limite = vencimiento(u(momento), criticidad)
        vencimientos.append(
            {
                "espera_desde_utc": momento + "+00:00",
                "criticidad": criticidad,
                "vence_en_utc": limite.astimezone(UTC).isoformat(timespec="seconds"),
                "vence_en_local": limite.astimezone(HUSO).isoformat(timespec="seconds"),
                "dia_local": limite.astimezone(HUSO).strftime("%A"),
                "por_que": por_que,
            }
        )

    decisiones = []
    for momento, criticidad, escalamientos, delta, por_que in DECISIONES:
        desde = u(momento)
        ahora = desde + delta
        fallo = resolver_vencimiento(
            trace_id="TR-VECTOR",
            criticidad=criticidad,
            espera_desde=desde,
            ahora=ahora,
            escalamientos=escalamientos,
        )
        decisiones.append(
            {
                "espera_desde_utc": momento + "+00:00",
                "criticidad": criticidad,
                "escalamientos_previos": escalamientos,
                "se_pregunta_en_utc": ahora.isoformat(timespec="seconds"),
                "accion": fallo.accion if fallo else None,
                "por_que": por_que,
            }
        )

    return {
        "_generado_por": "scripts/vectores_sla.py",
        "_fuente": "services/runlog/sla.py",
        "_contrato": (
            "El portal web reimplementa este calendario en TypeScript. Ambas "
            "implementaciones deben reproducir estos vectores exactamente. "
            "Ninguna accion al vencer puede ser 'aprobar' (regla dura, arquitectura v3 §7.3)."
        ),
        "_politicas": {
            "calendario": "registry/policies/calendario-laboral.yaml",
            "sla": "registry/policies/authority-gate.yaml -> hitl.sla",
        },
        # La configuracion con la que se generaron estos vectores, tal como quedo despues
        # de leer los YAML. El puerto de TypeScript la compara contra lo que el mismo lee:
        # reproducir los resultados con la configuracion equivocada seria acertar por suerte.
        "calendario": {
            "offset_horas": cal.huso.utcoffset(None).total_seconds() / 3600,
            "apertura": cal.apertura.isoformat(timespec="minutes"),
            "cierre": cal.cierre.isoformat(timespec="minutes"),
            "dias_habiles": list(cal.dias_habiles),
            "festivos": sorted(f.isoformat() for f in cal.festivos),
            "horas_por_dia": cal.horas_por_dia,
            "calibrado": cal.calibrado,
        },
        "sla": {
            criticidad: {
                "horas_habiles": r.horas_habiles,
                "dias_habiles": r.dias_habiles,
                "al_vencer": r.al_vencer,
                "luego": r.luego,
            }
            for criticidad, r in cargar_sla().items()
        },
        "vencimientos": vencimientos,
        "decisiones_al_vencer": decisiones,
    }


if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(construir(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"escrito: {DESTINO.relative_to(RAIZ)}")
