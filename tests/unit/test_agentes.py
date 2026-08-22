"""La capa de agentes: perfiles, reglas de convocatoria y memoria persistente."""

from __future__ import annotations

import pytest

from agents import memoria as memoria_mod
from agents.perfiles import PerfilDesconocido, cargar_perfiles, perfil
from agents.runtime import (
    AgenteNoDisponible,
    EncargoAmbiguo,
    PermisoDenegado,
    armar_contexto,
    convocar,
    recordar,
)
from office import bitacora


def encargo_valido(agente: str = "C-04", **cambios) -> dict:
    base = {
        "titulo": "Esquema de la tabla de tarifas",
        "descripcion": "Módulo: datos. Problema: falta vigencia. Restricción: sin migrar los CSV.",
        "entregable_esperado": "Esquema y migración",
        "convocado_por": "D5-01",
    }
    base.update(cambios)
    return {"agente_id": agente, **base}


def test_perfiles_incluyen_consultores_y_agentes_de_dominio():
    perfiles = cargar_perfiles()

    assert {"C-01", "C-05", "C-09"} <= set(perfiles)
    assert {"D5-01", "D5-02", "D5-03"} <= set(perfiles)
    assert perfiles["C-04"].nombre == "Dalia"
    assert perfiles["D5-01"].nombre == "Mateo"
    assert perfiles["C-04"].es_consultor
    assert not perfiles["D5-01"].es_consultor


def test_ningun_consultor_declara_acciones():
    """La regla dura de §5-bis: si necesitara un ACT-*, no es consultoría."""
    for identificador, quien in cargar_perfiles().items():
        if quien.es_consultor:
            assert quien.acciones == [], f"{identificador} declara acciones"


def test_agente_de_erp_tampoco_ejecuta_nada():
    """Lo que hace seguro adelantar D5: cero ACT-*, así la Fase 0 sigue sin ejecutar nada."""
    for identificador in ("D5-01", "D5-02", "D5-03"):
        assert perfil(identificador).acciones == []


def test_perfil_desconocido():
    with pytest.raises(PerfilDesconocido):
        perfil("D9-99")


def test_convocar_exige_encargo_escrito(oficina_temporal):
    """Un encargo sin problema ni entregable no arranca: el agente pediría contexto igual."""
    with pytest.raises(EncargoAmbiguo) as excinfo:
        convocar(**encargo_valido(descripcion="", entregable_esperado=""))

    assert "descripcion" in str(excinfo.value)
    assert "entregable" in str(excinfo.value)


def test_convocar_respeta_quien_puede_convocar(oficina_temporal):
    """§5-bis.3.1: a un consultor lo convocan Dirección o D5-01. Nadie más."""
    with pytest.raises(PermisoDenegado) as excinfo:
        convocar(**encargo_valido(convocado_por="Nay"))

    assert "no puede convocar" in str(excinfo.value)
    assert convocar(**encargo_valido(convocado_por="Gabriel")).agente == "C-04"


def test_convocar_bloquea_agente_fuera_de_fase(oficina_temporal):
    """D5-02 está en el registro pero sigue planned: no se le puede encargar nada."""
    with pytest.raises(AgenteNoDisponible) as excinfo:
        convocar(**encargo_valido("D5-02", convocado_por="Gabriel"))

    assert "planned" in str(excinfo.value)


def test_convocatoria_abre_trace_en_bitacora(oficina_temporal):
    encargo = convocar(**encargo_valido())

    entradas = bitacora.trace_de(encargo.id)
    assert len(entradas) == 1
    assert entradas[0].evento == "convocatoria"
    assert entradas[0].trace_id == encargo.trace_id
    assert entradas[0].autor == "D5-01"


def test_contexto_lleva_identidad_limites_y_memoria(oficina_temporal):
    recordar("C-04", "La tabla de tarifas necesita vigencia y versión.", tipo="decision", encargo="E-002")
    encargo = convocar(**encargo_valido())

    contexto = armar_contexto("C-04", encargo)

    assert "Eres **Dalia**" in contexto
    assert "Un campo mal nombrado se paga durante años" in contexto      # lema
    assert "Esquema, relaciones e integridad" in contexto                # habilidad del registro
    assert "aplicar migraciones en producción" in contexto               # lo que no hace
    assert "`ACT-*`: **ninguna**" in contexto
    assert "necesita vigencia y versión" in contexto                     # su memoria
    assert encargo.trace_id in contexto
    assert "Contrato de entregable" in contexto                          # contrato común


def test_memoria_es_append_only(oficina_temporal):
    memoria_mod.crear("C-04", "Dalia (C-04)", ["Esquema"])
    recordar("C-04", "Primera decisión.", tipo="decision", encargo="E-002")
    recordar("C-04", "Segunda decisión, que corrige la primera.", tipo="decision", encargo="E-002")

    memoria = memoria_mod.leer("C-04")

    assert [n.texto for n in memoria.notas] == [
        "Primera decisión.",
        "Segunda decisión, que corrige la primera.",
    ]
    assert memoria.recientes(1)[0].texto.startswith("Segunda")
    assert memoria.habilidades == ["Esquema"]


def test_crear_memoria_no_pisa_la_existente(oficina_temporal):
    memoria_mod.crear("C-07", "Tomás (C-07)", ["QA"])
    recordar("C-07", "Un caso que rompe el timeout.", encargo="E-008")

    memoria_mod.crear("C-07", "Tomás (C-07)", ["otra cosa"])

    memoria = memoria_mod.leer("C-07")
    assert memoria.habilidades == ["QA"]
    assert len(memoria.notas) == 1


def test_nota_vacia_o_de_tipo_invalido_se_rechaza(oficina_temporal):
    with pytest.raises(ValueError):
        memoria_mod.anotar("C-04", "   ")
    with pytest.raises(ValueError):
        memoria_mod.anotar("C-04", "texto", tipo="chisme")


# --- agentes listos: completos y sin encender (Fase 1) -----------------------


def test_los_dos_agentes_de_la_fase_1_estan_listos_no_construidos():
    """`listo` es el estado que faltaba: contrato entero, encendido pendiente."""
    for identificador in ("D4-03", "D2-03"):
        quien = perfil(identificador)
        assert quien.listo
        assert not quien.disponible
        assert quien.condiciones_pendientes, f"{identificador} listo sin nada pendiente"


def test_convocar_a_un_agente_listo_dice_exactamente_que_falta(oficina_temporal):
    """El rechazo no puede ser 'no disponible': tiene que nombrar la condición y su dueño."""
    from agents.runtime import AgenteSinEncender

    with pytest.raises(AgenteSinEncender) as excinfo:
        convocar(**encargo_valido("D4-03", convocado_por="Gabriel"))

    mensaje = str(excinfo.value)
    assert "Ivana (D4-03)" in mensaje
    assert "Margen objetivo" in mensaje
    assert "Nay" in mensaje


def test_el_prompt_de_un_agente_listo_se_escribe_igual(oficina_temporal):
    """Se revisa antes de encenderlo. Un prompt que nadie leyó no está listo."""
    from agents.runtime import escribir_prompts

    escritos = {p.stem for p in escribir_prompts()}

    assert {"D4-03", "D2-03"} <= escritos


def test_el_contexto_del_agente_de_pricing_dice_que_no_calcula_el_precio():
    contexto = armar_contexto("D4-03")

    assert "no calcula precio" in contexto
    assert "svc-pricing" in contexto
    assert "ACT-EMAIL-S" in contexto


def test_el_agente_de_costos_no_ejecuta_nada():
    """D2-03 analiza. Cambiar una tarifa por lo que encuentre es decisión de Dirección."""
    assert perfil("D2-03").acciones == []
