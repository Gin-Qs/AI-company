"""svc-alerts — motor de reglas sobre umbrales y selección del brief (§6.6, §9.2).

Regla dura del §9.2: **este servicio selecciona qué entra al brief diario; el agente que lo
narra —`D1-03`— no puede omitir ni añadir temas.** Si el modelo eligiera el contenido, el
sesgo entraría en lo primero que Dirección lee cada día, sin que nadie lo notara. Por eso:

* La severidad de cada alerta sale de un umbral en `registry/policies/alertas.yaml`, nunca de
  un juicio de la corrida.
* El mensaje de cada alerta es una plantilla armada con los datos de la propia alerta —igual
  que `svc-notify`—, nunca texto generado.
* `entra_al_brief` se calcula una sola vez, al construir la alerta, comparando su severidad
  contra `severidad_minima_brief` de la política. No es un campo que alguien pueda ajustar
  después: el agente recibe la lista ya decidida.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from services.ap.cuentas_por_pagar import Pagos
from services.ar.cartera import Cartera
from services.common.money import cantidad
from services.treasury.posicion import Tesoreria

RAIZ = Path(__file__).resolve().parent.parent.parent
REGLAS_POR_DEFECTO = RAIZ / "registry" / "policies" / "alertas.yaml"

ORDEN_SEVERIDAD = {"baja": 0, "media": 1, "alta": 2}


@dataclass(frozen=True)
class ReglasAlertas:
    version: str
    calibrado: bool
    severidad_minima_brief: str
    dias_de_caja_minimo: Decimal
    severidad_liquidez: str
    brecha_pp_minima: Decimal
    severidad_margen: str
    dias_vencido_alerta_media: int
    dias_vencido_alerta_alta: int
    dias_para_vencer_pagos: int
    severidad_pagos: str

    def entra_al_brief(self, severidad: str) -> bool:
        return ORDEN_SEVERIDAD.get(severidad, 0) >= ORDEN_SEVERIDAD.get(self.severidad_minima_brief, 2)


def cargar_reglas(ruta: str | Path | None = None) -> ReglasAlertas:
    destino = Path(ruta) if ruta else REGLAS_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}
    liquidez = datos.get("liquidez") or {}
    margen = datos.get("margen") or {}
    cartera = datos.get("cartera") or {}
    pagos = datos.get("pagos") or {}
    return ReglasAlertas(
        version=str(datos.get("version") or "v0"),
        calibrado=bool(datos.get("calibrado")),
        severidad_minima_brief=str(datos.get("severidad_minima_brief") or "alta"),
        dias_de_caja_minimo=cantidad(liquidez.get("dias_de_caja_minimo", 0)),
        severidad_liquidez=str(liquidez.get("severidad") or "alta"),
        brecha_pp_minima=cantidad(margen.get("brecha_pp_minima", 0)),
        severidad_margen=str(margen.get("severidad") or "alta"),
        dias_vencido_alerta_media=int(cartera.get("dias_vencido_alerta_media", 15)),
        dias_vencido_alerta_alta=int(cartera.get("dias_vencido_alerta_alta", 60)),
        dias_para_vencer_pagos=int(pagos.get("dias_para_vencer_alerta", 7)),
        severidad_pagos=str(pagos.get("severidad") or "media"),
    )


@dataclass(frozen=True)
class Alerta:
    alerta_id: str
    tipo: str            # liquidez | margen | cartera | pagos
    severidad: str        # baja | media | alta
    mensaje: str
    cifras: dict[str, str]
    fuente_servicio: str
    reglas_version: str
    entra_al_brief: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "alerta_id": self.alerta_id,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "cifras": self.cifras,
            "fuente_servicio": self.fuente_servicio,
            "reglas_version": self.reglas_version,
            "entra_al_brief": self.entra_al_brief,
        }


def _alerta_liquidez(tesoreria: Tesoreria, reglas: ReglasAlertas) -> Alerta | None:
    if tesoreria.dias_de_caja is None or tesoreria.dias_de_caja >= reglas.dias_de_caja_minimo:
        return None
    severidad = reglas.severidad_liquidez
    return Alerta(
        alerta_id="liquidez-dias-de-caja",
        tipo="liquidez",
        severidad=severidad,
        mensaje=(
            f"Días de caja en {tesoreria.dias_de_caja}, por debajo del mínimo de "
            f"{reglas.dias_de_caja_minimo}. Saldo actual $ {tesoreria.saldo_actual_mxn}."
        ),
        cifras={
            "dias_de_caja": str(tesoreria.dias_de_caja),
            "dias_de_caja_minimo": str(reglas.dias_de_caja_minimo),
            "saldo_actual_mxn": str(tesoreria.saldo_actual_mxn),
        },
        fuente_servicio="svc-treasury",
        reglas_version=reglas.version,
        entra_al_brief=reglas.entra_al_brief(severidad),
    )


def _alerta_margen(desviaciones: list, reglas: ReglasAlertas) -> Alerta | None:
    calificadas = [d for d in desviaciones if d.brecha_pp >= reglas.brecha_pp_minima]
    if not calificadas:
        return None
    peor = calificadas[0]  # svc-profitability ya entrega la lista ordenada por -brecha_pp
    severidad = reglas.severidad_margen
    return Alerta(
        alerta_id="margen-bajo-minimo",
        tipo="margen",
        severidad=severidad,
        mensaje=(
            f"{len(calificadas)} viaje(s) con margen bajo el mínimo de tarifa por "
            f"{reglas.brecha_pp_minima} puntos o más. El peor: {peor.trip_id} en la ruta "
            f"{peor.route_id}, {peor.brecha_pp} pp bajo el mínimo."
        ),
        cifras={
            "viajes_calificados": str(len(calificadas)),
            "peor_trip_id": peor.trip_id,
            "peor_route_id": peor.route_id,
            "peor_brecha_pp": str(peor.brecha_pp),
        },
        fuente_servicio="svc-profitability",
        reglas_version=reglas.version,
        entra_al_brief=reglas.entra_al_brief(severidad),
    )


def _alertas_cartera(cartera: Cartera, reglas: ReglasAlertas) -> list[Alerta]:
    alertas: list[Alerta] = []
    alta = [f for f in cartera.prioridad if f["dias_vencido"] >= reglas.dias_vencido_alerta_alta]
    media = [
        f
        for f in cartera.prioridad
        if reglas.dias_vencido_alerta_media <= f["dias_vencido"] < reglas.dias_vencido_alerta_alta
    ]
    if alta:
        total = sum((Decimal(f["saldo_mxn"]) for f in alta), Decimal("0.00"))
        alertas.append(
            Alerta(
                alerta_id="cartera-vencida-alta",
                tipo="cartera",
                severidad="alta",
                mensaje=(
                    f"{len(alta)} factura(s) vencidas por {reglas.dias_vencido_alerta_alta} días o más, "
                    f"por $ {total} en total."
                ),
                cifras={"facturas": str(len(alta)), "saldo_mxn": str(total)},
                fuente_servicio="svc-ar",
                reglas_version=reglas.version,
                entra_al_brief=reglas.entra_al_brief("alta"),
            )
        )
    if media:
        total = sum((Decimal(f["saldo_mxn"]) for f in media), Decimal("0.00"))
        alertas.append(
            Alerta(
                alerta_id="cartera-vencida-media",
                tipo="cartera",
                severidad="media",
                mensaje=(
                    f"{len(media)} factura(s) vencidas entre {reglas.dias_vencido_alerta_media} y "
                    f"{reglas.dias_vencido_alerta_alta} días, por $ {total} en total."
                ),
                cifras={"facturas": str(len(media)), "saldo_mxn": str(total)},
                fuente_servicio="svc-ar",
                reglas_version=reglas.version,
                entra_al_brief=reglas.entra_al_brief("media"),
            )
        )
    return alertas


def _semana(dia: date) -> str:
    return dia.strftime("%Y-W%V")


def _alerta_pagos(pagos: Pagos, reglas: ReglasAlertas, *, corte: date) -> Alerta | None:
    severidad = reglas.severidad_pagos
    if pagos.saldo_vencido_mxn > 0:
        return Alerta(
            alerta_id="pagos-vencidos",
            tipo="pagos",
            severidad=severidad,
            mensaje=f"$ {pagos.saldo_vencido_mxn} en cuentas por pagar ya vencidas.",
            cifras={"saldo_vencido_mxn": str(pagos.saldo_vencido_mxn)},
            fuente_servicio="svc-ap",
            reglas_version=reglas.version,
            entra_al_brief=reglas.entra_al_brief(severidad),
        )

    semanas_proximas = {
        _semana(corte + timedelta(days=d)) for d in range(reglas.dias_para_vencer_pagos + 1)
    }
    proximo = sum(
        (monto for semana, monto in pagos.calendario.items() if semana in semanas_proximas),
        Decimal("0.00"),
    )
    if proximo <= 0:
        return None
    return Alerta(
        alerta_id="pagos-por-vencer",
        tipo="pagos",
        severidad=severidad,
        mensaje=(
            f"$ {proximo} en cuentas por pagar vencen en los próximos "
            f"{reglas.dias_para_vencer_pagos} días."
        ),
        cifras={"saldo_por_vencer_mxn": str(proximo)},
        fuente_servicio="svc-ap",
        reglas_version=reglas.version,
        entra_al_brief=reglas.entra_al_brief(severidad),
    )


@dataclass(frozen=True)
class Seleccion:
    """El resultado completo: todas las alertas, y cuáles entran al brief.

    Separar las dos listas es a propósito: `alertas` es el registro completo para auditoría;
    `seleccion_para_el_brief` es exactamente lo que `D1-03` puede narrar — ni una alerta más,
    y la decisión ya está tomada en cada `Alerta.entra_al_brief`, no en cómo se lea la lista.
    """

    alertas: list[Alerta]
    reglas_version: str
    reglas_calibradas: bool

    @property
    def seleccion_para_el_brief(self) -> list[Alerta]:
        return [a for a in self.alertas if a.entra_al_brief]

    def as_dict(self) -> dict[str, object]:
        return {
            "reglas_version": self.reglas_version,
            "reglas_calibradas": self.reglas_calibradas,
            "alertas": [a.as_dict() for a in self.alertas],
        }


def evaluar(
    *,
    tesoreria: Tesoreria | None = None,
    cartera: Cartera | None = None,
    pagos: Pagos | None = None,
    desviaciones_margen: list | None = None,
    corte: date | None = None,
    reglas: ReglasAlertas | None = None,
) -> Seleccion:
    """Evalúa todas las reglas sobre lo que se le pase. Cada entrada es opcional a propósito:
    un panorama sin `svc-ap` construido todavía sigue produciendo alertas de caja y cartera.
    """
    reglas = reglas or cargar_reglas()
    alertas: list[Alerta] = []

    if tesoreria is not None:
        alerta = _alerta_liquidez(tesoreria, reglas)
        if alerta:
            alertas.append(alerta)

    if desviaciones_margen:
        alerta = _alerta_margen(desviaciones_margen, reglas)
        if alerta:
            alertas.append(alerta)

    if cartera is not None:
        alertas.extend(_alertas_cartera(cartera, reglas))

    if pagos is not None:
        alerta = _alerta_pagos(pagos, reglas, corte=corte or date.today())
        if alerta:
            alertas.append(alerta)

    return Seleccion(alertas=alertas, reglas_version=reglas.version, reglas_calibradas=reglas.calibrado)
