"""Siembra la oficina: memorias, backlog del ERP y estado inicial.

Idempotente: se puede correr las veces que haga falta. No sobreescribe memorias ni duplica
encargos; solo crea lo que falte.

    python scripts/sembrar_oficina.py

El backlog que siembra no es de relleno: es el camino real para terminar el ERP, y su primer
hito es la bandeja de HITL, que la §17.5 pone como requisito de entrada de la Fase 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import memoria as memoria_mod  # noqa: E402
from agents.perfiles import cargar_perfiles  # noqa: E402
from agents.runtime import convocar, escribir_prompts, recordar  # noqa: E402
from office import encargos as encargos_mod  # noqa: E402

# (id, agente, titulo, descripcion, entregable, depende_de, hitl)
BACKLOG_ERP = [
    (
        "E-001", "D5-01", "Requerimientos de la bandeja única de HITL",
        "Módulo: panel del ERP. Problema: las aprobaciones viven hoy en WhatsApp y correo, así que "
        "el Gate de Autoridad existe en el papel y no en la operación. Restricción: una sola bandeja, "
        "con trace_id, umbral disparado, resumen de una línea, entregable enlazado y SLA visible (§7.2).",
        "Lista de requerimientos con criterio de aceptación por cada uno.", [], False,
    ),
    (
        "E-002", "C-04", "Esquema de datos v1 del ERP",
        "Módulo: base de datos. Problema: el catálogo vive en CSV y no aguanta la bandeja de HITL ni "
        "el histórico de viajes. Restricción: tiene que recibir sin pérdida lo que hoy produce "
        "svc-masterdata, y versionar la tabla de tarifas con su vigencia.",
        "Esquema, relaciones, migraciones iniciales y diccionario de datos.", ["E-001"], False,
    ),
    (
        "E-003", "C-03", "Servicios y reglas de negocio del módulo HITL",
        "Módulo: backend. Problema: falta el flujo aprobar/rechazar/expirar con su regla de timeout "
        "(§7.3). Restricción: el timeout no puede interpretarse como aprobación, nunca.",
        "Diseño de servicios, máquina de estados y manejo de errores.", ["E-002"], False,
    ),
    (
        "E-004", "C-01", "Flujo de pantalla de la bandeja",
        "Módulo: producto/UX. Problema: quien aprueba necesita decidir en segundos y hoy no ve el "
        "SLA. Restricción: el owner del equipo es quien recibe; el orden lo manda el vencimiento.",
        "Dos flujos alternativos con wireframes y su comparación.", ["E-001"], False,
    ),
    (
        "E-005", "C-02", "Componentes y design system del panel",
        "Módulo: frontend. Problema: sin sistema de componentes cada pantalla del ERP inventará el "
        "suyo. Restricción: se construye una sola vez y sirve para los módulos que siguen.",
        "Inventario de componentes, tokens y guía de uso.", ["E-004"], False,
    ),
    (
        "E-006", "C-05", "Integraciones del ERP: Airtable, GPS y banca",
        "Módulo: integraciones. Problema: la bandeja vive hoy en Airtable y los datos de operación "
        "llegan de GPS y banca por archivo. Restricción: idempotencia y reintentos; el sistema del "
        "otro va a fallar.",
        "Contratos de endpoint, webhooks y política de reintento.", ["E-002"], False,
    ),
    (
        "E-007", "C-06", "Matriz de roles y accesos del ERP",
        "Módulo: seguridad. Problema: no hay matriz de permisos y el ERP va a manejar datos de "
        "clientes y de operadores. Restricción: mínimo privilegio; precursor de svc-rbac (fase 6).",
        "Matriz de roles, revisión de superficie de ataque y plan de autenticación.", ["E-002"], False,
    ),
    (
        "E-008", "C-07", "Criterios de aceptación y regresión del módulo HITL",
        "Módulo: QA. Problema: sin criterios verificables no se puede declarar el módulo terminado. "
        "Restricción: el caso de timeout y el de doble aprobación tienen que estar cubiertos.",
        "Casos de prueba, criterios de aceptación y plan de regresión.", ["E-003"], False,
    ),
    (
        "E-009", "C-08", "Ambientes, despliegue y respaldo del ERP",
        "Módulo: DevOps. Problema: no hay ambientes ni plan de recuperación. Restricción: tiene que "
        "poder revertirse un despliegue malo sin perder la bandeja.",
        "Plan de ambientes, despliegue, monitoreo, respaldo y recuperación.", ["E-003"], False,
    ),
    (
        "E-010", "C-09", "Diccionario de datos y guía de onboarding del ERP",
        "Módulo: documentación. Problema: lo que se decida aquí lo va a mantener alguien que no "
        "estuvo. Restricción: prosa corta, sin duplicar lo que ya dice la arquitectura.",
        "Diccionario de datos, changelog y guía de onboarding.", ["E-002", "E-003"], False,
    ),
    (
        "E-011", "D5-03", "Evaluación de calidad de los primeros entregables de consultoría",
        "Módulo: AgentOps. Problema: con doce agentes disponibles la calidad ya no se vigila a mano "
        "(§15). Restricción: se evalúa sobre muestra registrada en bitácora, no de memoria.",
        "Rúbrica de evaluación aplicada a una muestra, con hallazgos de deriva y costo.", ["E-002"], False,
    ),
    (
        "E-012", "D5-01", "Alcance del MVP del ERP para autorización de Dirección",
        "Módulo: producto. Problema: hay que cerrar qué entra al MVP del ERP y qué se pospone. "
        "Restricción: el MVP tiene que cubrir la bandeja de HITL o la Fase 1 no arranca.",
        "Propuesta de alcance con opciones y su costo, para decisión de Gabriel.",
        ["E-001", "E-002"], True,
    ),
]

# Estado inicial: lo que ya está en marcha. El resto queda pendiente en el backlog.
AVANCES = [
    ("E-001", "en_curso", "Mateo", "Requerimientos en redacción con la operación real de Fleeter"),
    ("E-002", "en_curso", "Dalia", "Esquema en revisión contra lo que produce svc-masterdata"),
    ("E-012", "bloqueado", "Mateo", "Espera decisión de alcance de Gabriel: es un CTL-HITL"),
]

NOTAS = [
    ("D5-01", "La bandeja de HITL no es un módulo más del ERP: es lo que bloquea la Fase 1 completa "
              "(§17.5). Si algo se pospone, no es esto.", "decision", "E-001"),
    ("C-04", "El catálogo de la Fase 0 ya define las cinco entidades maestras y sus llaves. El esquema "
             "del ERP las hereda en vez de reinventarlas; cambiar los nombres costaría migrar los CSV.",
     "decision", "E-002"),
    ("C-04", "La tabla de tarifas necesita vigencia y versión, no sólo precio: es la tabla pre-aprobada "
             "que Gabriel actualiza cada mes y hay que poder reconstruir qué precio aplicaba en qué fecha.",
     "trampa", "E-002"),
    ("D5-03", "Con 12 agentes disponibles ya se cruzó el umbral de ~8 que la arquitectura pone para "
              "encender AgentOps. La primera evaluación sale sobre los entregables del ERP.",
     "contexto", "E-011"),
]


def sembrar_memorias() -> int:
    creadas = 0
    for agente_id, quien in sorted(cargar_perfiles().items()):
        if not quien.disponible:
            continue
        destino = memoria_mod.ruta(agente_id)
        if destino.is_file():
            continue
        memoria_mod.crear(agente_id, f"{quien.nombre} ({agente_id}) - {quien.puesto}", quien.habilidades)
        creadas += 1
    return creadas


def sembrar_encargos() -> int:
    existentes = encargos_mod.cargar_todos()
    creados = 0
    for encargo_id, agente, titulo, descripcion, entregable, depende, hitl in BACKLOG_ERP:
        if encargo_id in existentes:
            continue
        # Quien convoca importa: §5-bis.3.1 sólo permite a Dirección o a D5-01.
        convocado_por = "Gabriel" if agente.startswith("D5") else "D5-01"
        encargo = convocar(
            agente,
            titulo=titulo,
            descripcion=descripcion,
            entregable_esperado=entregable,
            convocado_por=convocado_por,
            depende_de=depende,
            hitl=hitl,
        )
        # convocar() asigna el siguiente id libre; lo fijamos al del backlog para que sea estable.
        if encargo.id != encargo_id:
            encargos_mod.ruta(encargo.id).unlink()
            encargo.id = encargo_id
            encargos_mod.guardar(encargo)
        creados += 1
    return creados


def aplicar_avances() -> int:
    aplicados = 0
    for encargo_id, estado, autor, nota in AVANCES:
        encargo = encargos_mod.cargar(encargo_id)
        if encargo.estado == estado:
            continue
        try:
            encargos_mod.avanzar(encargo_id, estado, autor=autor, nota=nota)
            aplicados += 1
        except encargos_mod.TransicionInvalida:
            continue
    return aplicados


def sembrar_notas() -> int:
    escritas = 0
    for agente_id, texto, tipo, encargo in NOTAS:
        memoria = memoria_mod.leer(agente_id)
        if any(nota.texto[:40] == " ".join(texto.split())[:40] for nota in memoria.notas):
            continue
        recordar(agente_id, texto, tipo=tipo, encargo=encargo)
        escritas += 1
    return escritas


def main() -> int:
    memorias = sembrar_memorias()
    creados = sembrar_encargos()
    avances = aplicar_avances()
    notas = sembrar_notas()
    prompts = escribir_prompts()

    print(f"memorias creadas:  {memorias}")
    print(f"encargos creados:  {creados}")
    print(f"avances aplicados: {avances}")
    print(f"notas escritas:    {notas}")
    print(f"prompts generados: {len(prompts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
