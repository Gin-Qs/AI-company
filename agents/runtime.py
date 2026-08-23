"""Runtime de la oficina: convocar a un agente y armarle su contexto.

Lo que hace este modulo, en una linea: **aplica las reglas antes de que el modelo hable.**

* Quien puede convocar a quien (§5-bis.3.1).
* Que un encargo ambiguo no arranque (§5-bis.3.2).
* Que un consultor no tenga ACT-* jamas (§5-bis.1, regla dura).
* Que toda convocatoria abra un trace en la bitacora (§5-bis.3.5, R7).

Lo que NO hace: llamar a un modelo. El contexto que arma se le entrega a quien vaya a razonar
—hoy, Claude Code, que es literalmente como el organigrama describe al equipo de T05-02:
"ingenieria humana asistida con Claude Code". Cuando exista un runtime de LLM propio, se
conecta aqui y ni las reglas ni la memoria cambian.
"""

from __future__ import annotations

from pathlib import Path

from agents import memoria as memoria_mod
from agents.perfiles import Perfil, cargar_perfiles, perfil
from office import bitacora
from office.estado import leer_pausa
from office.encargos import Encargo, cargar as cargar_encargo, crear as crear_encargo

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "agents" / "base.md"
DIR_PROMPTS = RAIZ / "agents" / "prompts"


class PermisoDenegado(PermissionError):
    """Alguien intento convocar a un agente que no le corresponde convocar."""


class EncargoAmbiguo(ValueError):
    """Falta el que, el por que o el para que. El agente pide contexto, no lo inventa."""


class AgenteNoDisponible(RuntimeError):
    """El agente existe en el registro pero su fase no llego."""


class AgenteSinEncender(AgenteNoDisponible):
    """El agente esta completo y no se enciende: le faltan condiciones de entrada.

    Se distingue de `AgenteNoDisponible` a proposito. "Su fase no llego" y "esta listo y
    faltan dos condiciones que alguien tiene que cerrar" son dos situaciones distintas, y
    la segunda tiene dueno y fecha.
    """


class OficinaEnPausa(RuntimeError):
    """La oficina esta detenida por decision escrita en office/pausa.yaml."""


class AgenteRetirado(AgenteNoDisponible):
    """El agente fue dado de baja. No se convoca, y su historia sigue consultable.

    Se distingue de `AgenteSinEncender` y de `AgenteNoDisponible` porque las tres tienen
    salidas distintas: uno espera condiciones, otro espera su fase, y este no espera nada.
    Decirle "todavia no" a alguien cuyo agente se retiro hace tres meses lo manda a esperar
    algo que no va a pasar.
    """


def convocar(
    agente_id: str,
    *,
    titulo: str,
    descripcion: str,
    entregable_esperado: str,
    convocado_por: str,
    depende_de: list[str] | None = None,
    hitl: bool = False,
) -> Encargo:
    """Abre un encargo con todas las reglas aplicadas. Devuelve el encargo ya registrado."""
    pausa = leer_pausa()
    if pausa.get("activa"):
        raise OficinaEnPausa(
            f"la oficina esta en pausa desde {pausa.get('desde')} por {pausa.get('por')}. "
            f"Se reanuda cuando: {' '.join(str(pausa.get('se_reanuda_cuando', '')).split())}"
        )

    quien = perfil(agente_id)

    # El retiro se comprueba antes que nada: un agente dado de baja no tiene condiciones
    # de encendido pendientes ni fase por llegar. No hay nada que esperar.
    if quien.retirado:
        retiro = quien.retiro
        cubre = retiro.get("lo_cubre") or "nadie declarado"
        raise AgenteRetirado(
            f"{quien.etiqueta} fue retirado el {retiro.get('fecha', 'sin fecha')} "
            f"por {retiro.get('por', 'sin responsable')}: {retiro.get('motivo', 'sin motivo declarado')} "
            f"Su trabajo lo cubre ahora: {cubre}. "
            f"Su historia sigue en el registro; lo que no vuelve es el agente."
        )

    if quien.listo:
        pendientes = quien.condiciones_pendientes
        detalle = "; ".join(
            f"{c.get('condicion')} (lo cierra {c.get('responsable', 'sin responsable')})" for c in pendientes
        )
        raise AgenteSinEncender(
            f"{quien.etiqueta} esta listo pero sin encender: "
            f"faltan {len(pendientes)} de {len(quien.condiciones_encendido)} condiciones. {detalle}"
        )

    if not quien.disponible:
        raise AgenteNoDisponible(
            f"{quien.etiqueta} esta {quien.estado}: su fase no ha llegado. "
            f"Adelantarlo es una decision de Direccion y se escribe en el registro."
        )

    # Regla dura de §5-bis.1: si un consultor necesitara un ACT-*, el trabajo no es de
    # consultoria. Se verifica en cada convocatoria, no solo en el validador.
    if quien.es_consultor and quien.acciones:
        raise PermisoDenegado(
            f"{quien.etiqueta} declara acciones {quien.acciones}: un consultor no ejecuta jamas"
        )

    if quien.convocable_por and convocado_por not in quien.convocable_por:
        raise PermisoDenegado(
            f"{convocado_por} no puede convocar a {quien.etiqueta}; "
            f"solo pueden: {', '.join(quien.convocable_por)}"
        )

    faltantes = [
        campo
        for campo, valor in (("titulo", titulo), ("descripcion", descripcion), ("entregable", entregable_esperado))
        if not str(valor).strip()
    ]
    if faltantes:
        raise EncargoAmbiguo(
            f"encargo incompleto para {quien.etiqueta}: falta {', '.join(faltantes)}. "
            f"Un encargo lleva que modulo, que problema y que restriccion (§5-bis.3.2)"
        )

    return crear_encargo(
        titulo=titulo,
        agente=agente_id,
        convocado_por=convocado_por,
        descripcion=descripcion,
        entregable_esperado=entregable_esperado,
        depende_de=depende_de,
        hitl=hitl,
    )


def recordar(agente_id: str, texto: str, *, tipo: str = "aprendizaje", encargo: str = "-") -> None:
    """Escribe en la memoria del agente y lo deja anotado en la bitacora.

    Si la nota pertenece a un encargo, hereda su trace: la memoria y el caso tienen que poder
    leerse juntos, que es justo lo que pide la trazabilidad de §8.
    """
    nota = memoria_mod.anotar(agente_id, texto, tipo=tipo, encargo=encargo)
    trace = None
    if encargo and encargo != "-":
        try:
            trace = cargar_encargo(encargo).trace_id
        except KeyError:
            trace = None
    bitacora.registrar(
        evento="nota",
        agente=agente_id,
        encargo=encargo,
        detalle=f"[{nota.tipo}] {nota.texto}",
        trace_id=trace,
    )


def armar_contexto(agente_id: str, encargo: Encargo | None = None) -> str:
    """El prompt completo del agente: contrato comun + quien es + que sabe + que se le pide."""
    quien = perfil(agente_id)
    memoria = memoria_mod.leer(agente_id)

    partes = [BASE.read_text(encoding="utf-8"), "", "---", "", _bloque_identidad(quien)]

    habilidades = memoria.habilidades or quien.habilidades
    if habilidades:
        partes += ["## Para qué se te convoca", ""] + [f"- {h}" for h in habilidades] + [""]

    if quien.no_hace:
        partes += ["## Lo que no haces", ""] + [f"- {n}" for n in quien.no_hace] + [""]

    partes += ["## Autoridad", ""]
    partes.append(
        f"- Acciones `ACT-*`: **{', '.join(quien.acciones) if quien.acciones else 'ninguna'}**"
        + ("" if quien.acciones else " — produces texto y código, no ejecutas nada en la operación.")
    )
    if quien.herramientas:
        partes.append(f"- Servicios conectados hoy: {', '.join(quien.herramientas)}")
    if quien.herramientas_planeadas:
        partes.append(
            f"- Servicios que aún no existen: {', '.join(quien.herramientas_planeadas)} "
            f"— no los cites como si respondieran."
        )
    if quien.convocable_por:
        partes.append(f"- Te convoca: {', '.join(quien.convocable_por)}. Nadie más.")
    partes.append("")

    if quien.listo:
        # Un prompt que no dice que el agente está apagado se lee como si estuviera operando.
        partes += [
            "## Todavía no estás encendido",
            "",
            "Tu contrato está completo y nadie puede convocarte hasta que se cierren estas",
            "condiciones. Están en tu registro, no en la memoria de nadie:",
            "",
        ]
        for condicion in quien.condiciones_encendido:
            marca = "x" if condicion.get("cumplida") else " "
            responsable = condicion.get("responsable", "sin responsable")
            partes.append(f"- [{marca}] {condicion.get('condicion')} — *{responsable}*")
        partes.append("")

    if memoria.notas:
        partes += ["## Tu memoria", "", "Lo que ya sabes de encargos anteriores:", ""]
        for nota in memoria.recientes(8):
            partes.append(f"- **{nota.fecha}** · `{nota.encargo}` · *{nota.tipo}* — {nota.texto}")
        partes.append("")

    if encargo is not None:
        partes += [
            "## Encargo",
            "",
            f"**{encargo.id} — {encargo.titulo}**",
            "",
            encargo.descripcion or "(sin descripción)",
            "",
            f"- Entregable esperado: {encargo.entregable_esperado or '(sin especificar)'}",
            f"- Convocado por: {encargo.convocado_por}",
            f"- Trace: `{encargo.trace_id}`",
        ]
        if encargo.depende_de:
            partes.append(f"- Depende de: {', '.join(encargo.depende_de)}")
        if encargo.hitl:
            partes.append("- **Requiere aprobación humana antes de cerrarse.**")
        partes.append("")

    return "\n".join(partes).rstrip() + "\n"


def _bloque_identidad(quien: Perfil) -> str:
    lineas = ["## Quién eres", "", f"Eres **{quien.nombre}**, {quien.puesto} (`{quien.agente_id}`)."]
    if quien.lema:
        lineas.append(f'Tu forma de trabajar cabe en una frase: *"{quien.lema}"*')
    if quien.voz:
        lineas.append(quien.voz)
    if quien.mision:
        lineas += ["", f"**Misión.** {quien.mision}"]
    lineas.append("")
    return "\n".join(lineas)


def escribir_prompts() -> list[Path]:
    """Vuelca el contexto de cada agente a agents/prompts/ para poder leerlo y versionarlo.

    Los prompts son generados a proposito: la fuente de verdad es el registro mas la memoria.
    Editar el prompt a mano seria crear una segunda verdad que nadie sincroniza.
    """
    DIR_PROMPTS.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []
    for agente_id, quien in sorted(cargar_perfiles().items()):
        # Los `listo` tambien: su prompt se escribe y se revisa antes de encenderlos, que es
        # justo para lo que sirve tenerlos listos.
        if not quien.disponible and not quien.listo:
            continue
        destino = DIR_PROMPTS / f"{agente_id}.md"
        destino.write_text(
            "<!-- GENERADO por agents/runtime.py:escribir_prompts(). No editar a mano:\n"
            "     la fuente es registry/ + office/identidades.yaml + agents/memoria/. -->\n\n"
            + armar_contexto(agente_id),
            encoding="utf-8",
        )
        escritos.append(destino)
    return escritos
