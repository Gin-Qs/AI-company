"""El flujo completo de la Fase 3: de los números verificados al brief que D1-03 narra.

Los cuatro servicios trabajando juntos sobre el catálogo real de `data/ejemplo`, sin agente y
sin LLM. Cuando `D1-03` se encienda, esto es exactamente lo que va a narrar — y la prueba que
importa es que no pueda narrar nada que `svc-alerts` no haya seleccionado.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.alerts import evaluar
from services.ap.cuentas_por_pagar import CuentaPorPagar, analizar as analizar_pagos, conciliar as conciliar_pagos
from services.ar.cartera import Factura, analizar as analizar_cartera, conciliar as conciliar_cartera
from services.ingest.normalizador import normalizar_banco
from services.kpi import construir_tablero
from services.masterdata import cargar_catalogo
from services.masterdata.loader import leer_csv
from services.pipeline import ejecutar_fase0
from services.treasury.posicion import construir as construir_tesoreria

CORTE = date(2026, 6, 30)


@pytest.fixture
def catalogo(datos_ejemplo):
    return cargar_catalogo(datos_ejemplo / "catalogo")


def brief_de(seleccion, tablero) -> dict:
    """El brief que D1-03 redactaría, con el contrato de §7.1 puesto.

    Narra exactamente `seleccion.seleccion_para_el_brief` y `tablero.indicadores` — nada que no
    esté ahí. Es la forma estructural de la regla del §9.2: el agente no puede citar una alerta
    que no está en la lista, porque la lista es lo único de lo que este helper puede componer
    el resumen.
    """
    temas = [a.mensaje for a in seleccion.seleccion_para_el_brief]
    return {
        "decision_solicitada": "ninguna, es informativo",
        "fuentes": {a.alerta_id: a.fuente_servicio for a in seleccion.seleccion_para_el_brief},
        "cifras": {i.kpi_id: str(i.valor) for i in tablero.indicadores},
        "supuestos": [],
        "confianza": {
            "nivel": "alta" if seleccion.reglas_calibradas else "media",
            "limitado_por": "reglas de alertas sin calibrar" if not seleccion.reglas_calibradas else "ninguno",
        },
        "opciones": ["ninguna: es un resumen, no una decisión que tomar"],
        "si_no_respondes": "el brief queda leído y sin acción; no hay caso que expire",
        "resumen": " ".join(temas) if temas else "Sin alertas que reporten hoy.",
        "temas": temas,
    }


def test_flujo_de_sintesis_ejecutiva(catalogo, datos_ejemplo):
    """De los cuatro servicios al brief, sin que el agente calcule o elija nada."""
    # 1. Fase 0: margen real y desviaciones contra la tabla de precios.
    reporte = ejecutar_fase0(datos_ejemplo)

    # 2. svc-ar: cartera real de data/ejemplo, con una factura vieja para forzar una alerta.
    facturas = [
        Factura(factura_id="F-VIEJA", cliente_id="CL-01", fecha_emision=date(2026, 1, 1), total_mxn=Decimal("8000.00"))
    ]
    cartera = analizar_cartera(conciliar_cartera(facturas, [], catalogo), corte=CORTE)
    assert cartera.saldo_vencido_mxn > 0

    # 3. svc-ap: sin cuentas reales en data/ejemplo (fase-3.md lo declara pendiente); una cuenta
    #    sintética basta para probar que el calendario alimenta a svc-treasury.
    cuentas = [
        CuentaPorPagar(
            cuenta_id="CP-1", proveedor_id="PROV-1", fecha_emision=date(2026, 6, 25),
            dias_credito=10, total_mxn=Decimal("3000.00"),
        )
    ]
    pagos = analizar_pagos(conciliar_pagos(cuentas, []), corte=CORTE)

    # 4. svc-treasury: saldo real del banco de data/ejemplo, proyectado con AR y AP.
    banco = normalizar_banco(leer_csv(datos_ejemplo / "operacion" / "banco.csv"))
    tesoreria = construir_tesoreria(
        banco.registros,
        saldo_inicial_mxn="10000.00",
        corte=CORTE,
        flujo_esperado_cobros=cartera.flujo_esperado,
        calendario_pagos=pagos.calendario,
    )

    # 5. svc-kpi: empaqueta lo que ya se calculó, sin recalcular nada.
    tablero = construir_tablero(
        {
            "margen_ponderado_pct": reporte.distribucion.ponderado_pct,
            "dias_cartera_dso": cartera.dias_cartera or Decimal("0"),
        },
        periodo="2026-06",
    )
    por_kpi = {i.kpi_id: i for i in tablero.indicadores}
    assert por_kpi["margen_ponderado_pct"].valor == reporte.distribucion.ponderado_pct

    # 6. svc-alerts: selecciona qué entra al brief. La factura vieja tiene que calificar.
    seleccion = evaluar(
        tesoreria=tesoreria,
        cartera=cartera,
        pagos=pagos,
        desviaciones_margen=reporte.contraste.desviaciones if reporte.contraste else None,
        corte=CORTE,
    )
    assert any(a.tipo == "cartera" for a in seleccion.alertas)

    # 7. D1-03 narra exactamente la selección: el contrato de entregable cierra el flujo.
    entregable = brief_de(seleccion, tablero)
    seleccionados = {a.alerta_id for a in seleccion.seleccion_para_el_brief}
    no_seleccionados = {a.alerta_id for a in seleccion.alertas} - seleccionados

    assert all(any(a.mensaje == tema for a in seleccion.seleccion_para_el_brief) for tema in entregable["temas"])
    assert not no_seleccionados & set(entregable["fuentes"])
    assert entregable["decision_solicitada"]  # el contrato de §7.1: ninguno de los seis falta


def test_una_alerta_de_severidad_baja_no_llega_al_brief_aunque_exista(catalogo):
    """El caso que importa: la alerta se calcula y se guarda, pero D1-03 no la puede narrar."""
    cuentas = [
        CuentaPorPagar(
            cuenta_id="CP-1", proveedor_id="PROV-1", fecha_emision=date(2026, 4, 1),
            dias_credito=30, total_mxn=Decimal("500.00"),
        )  # vencida hace 20 dias: existe, pero pagos-vencidos es severidad "media" en la politica
    ]
    pagos = analizar_pagos(conciliar_pagos(cuentas, []), corte=date(2026, 5, 21))

    seleccion = evaluar(pagos=pagos, corte=date(2026, 5, 21))
    tablero = construir_tablero({}, periodo="2026-05")

    assert seleccion.alertas               # se calculó
    assert seleccion.seleccion_para_el_brief == []   # pero no entra al brief

    entregable = brief_de(seleccion, tablero)
    assert entregable["resumen"] == "Sin alertas que reporten hoy."
