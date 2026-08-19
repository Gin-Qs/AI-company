"""svc-notify — avisos por plantilla fija, sin LLM (§6.6).

El servicio más pequeño de la Fase 2 y el que sostiene una regla del Gate: *"toda `ACT-EMAIL-S`
externa es `CTL-HITL`, **salvo plantilla fija de `svc-notify` con variables validadas, que no
pasa por LLM**"* (§11.4). Es decir: esta caja es la razón por la que un recordatorio de pago no
necesita despertar a nadie a las once de la noche.

Por eso su diseño es una lista de negativas:

* **No genera texto.** Renderiza una plantilla aprobada. No hay parámetro para texto libre.
* **No adivina variables.** Falta una, o llega con el tipo que no es, y el mensaje no sale.
* **No manda a cualquiera.** El destinatario existe en `svc-masterdata` o no hay envío.
* **No inventa el envío.** Sin canal contratado, el mensaje se registra y lo manda una persona;
  devolver "enviado" sin haber enviado sería la peor forma posible de fallar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from services.common.errors import ErrorDeServicio
from services.masterdata.catalogo import Catalogo

RAIZ = Path(__file__).resolve().parent.parent.parent
PLANTILLAS_POR_DEFECTO = RAIZ / "registry" / "policies" / "plantillas-notify.yaml"

HUECO = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PlantillaDesconocida(ErrorDeServicio):
    """Se pidió una plantilla que no está aprobada. No hay plantilla improvisada."""

    codigo = "NOTIFY-PLANTILLA-DESCONOCIDA"


class VariableInvalida(ErrorDeServicio):
    """Falta una variable, sobra, o no es del tipo declarado. El mensaje no sale."""

    codigo = "NOTIFY-VARIABLE"


class DestinatarioDesconocido(ErrorDeServicio):
    """El destinatario no está en el catálogo. No se manda a una dirección suelta."""

    codigo = "NOTIFY-DESTINATARIO"


class CanalNoDisponible(ErrorDeServicio):
    """El canal existe en la política pero está apagado."""

    codigo = "NOTIFY-CANAL"


@dataclass(frozen=True)
class Variable:
    nombre: str
    tipo: str          # texto | importe | fecha | entero
    obligatoria: bool = True


@dataclass(frozen=True)
class Plantilla:
    plantilla_id: str
    canal: str
    asunto: str
    texto: str
    destinatarios: tuple[str, ...]
    variables: dict[str, Variable]


@dataclass(frozen=True)
class CatalogoPlantillas:
    version: str
    aprobadas: bool
    canales: dict[str, dict]
    plantillas: dict[str, Plantilla]

    def plantilla(self, plantilla_id: str) -> Plantilla:
        if plantilla_id not in self.plantillas:
            raise PlantillaDesconocida(
                f"no existe la plantilla {plantilla_id!r}; aprobadas: {', '.join(sorted(self.plantillas))}",
                campo="plantilla_id",
            )
        return self.plantillas[plantilla_id]

    def canal_activo(self, canal: str) -> bool:
        return bool((self.canales.get(canal) or {}).get("activo"))

    def entrega_de(self, canal: str) -> str:
        """`externa` sale solo; `registro` queda escrito y lo manda una persona."""
        return str((self.canales.get(canal) or {}).get("entrega") or "registro")


def cargar_plantillas(ruta: str | Path | None = None) -> CatalogoPlantillas:
    destino = Path(ruta) if ruta else PLANTILLAS_POR_DEFECTO
    datos = yaml.safe_load(destino.read_text(encoding="utf-8")) or {}

    plantillas: dict[str, Plantilla] = {}
    for identificador, crudo in (datos.get("plantillas") or {}).items():
        variables = {
            nombre: Variable(
                nombre=nombre,
                tipo=str((definicion or {}).get("tipo") or "texto"),
                obligatoria=bool((definicion or {}).get("obligatoria", True)),
            )
            for nombre, definicion in ((crudo.get("variables") or {}).items())
        }
        texto = " ".join(str(crudo.get("texto") or "").split())
        asunto = str(crudo.get("asunto") or "").strip()

        # Un hueco en el texto sin variable declarada es una plantilla rota: se detecta al
        # cargar el catalogo, no al intentar mandarle algo a un cliente.
        huecos = set(HUECO.findall(texto)) | set(HUECO.findall(asunto))
        faltan = huecos - set(variables)
        if faltan:
            raise VariableInvalida(
                f"la plantilla {identificador} usa {', '.join(sorted(faltan))} sin declararlas",
                campo="variables",
            )

        plantillas[str(identificador)] = Plantilla(
            plantilla_id=str(identificador),
            canal=str(crudo.get("canal") or "bitacora"),
            asunto=asunto,
            texto=texto,
            destinatarios=tuple(str(d) for d in (crudo.get("destinatarios") or [])),
            variables=variables,
        )

    return CatalogoPlantillas(
        version=str(datos.get("version") or "v0"),
        aprobadas=bool(datos.get("aprobadas")),
        canales=dict(datos.get("canales") or {}),
        plantillas=plantillas,
    )


@dataclass
class Mensaje:
    plantilla_id: str
    canal: str
    destinatario_id: str
    asunto: str
    texto: str
    plantillas_version: str
    aprobada: bool
    variables: dict[str, str] = field(default_factory=dict)
    generado: str = ""

    @property
    def paso_por_llm(self) -> bool:
        """Constante con nombre. Si alguna vez esto pudiera ser `True`, el gate cambia."""
        return False

    def as_dict(self) -> dict[str, object]:
        return {
            "plantilla_id": self.plantilla_id,
            "canal": self.canal,
            "destinatario_id": self.destinatario_id,
            "asunto": self.asunto,
            "texto": self.texto,
            "variables": self.variables,
            "plantillas_version": self.plantillas_version,
            "aprobada": self.aprobada,
            "paso_por_llm": self.paso_por_llm,
            "generado": self.generado,
        }


def _convertir(valor: object, variable: Variable) -> str:
    """Valida el tipo declarado y devuelve el texto que entra en el hueco."""
    if variable.tipo == "importe":
        try:
            return str(Decimal(str(valor)).quantize(Decimal("0.01")))
        except (InvalidOperation, ArithmeticError) as exc:
            raise VariableInvalida(
                f"{variable.nombre} debe ser un importe y llego {valor!r}", campo=variable.nombre
            ) from exc
    if variable.tipo == "fecha":
        if isinstance(valor, (date, datetime)):
            return valor.strftime("%Y-%m-%d")
        try:
            return datetime.strptime(str(valor), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError as exc:
            raise VariableInvalida(
                f"{variable.nombre} debe ser una fecha AAAA-MM-DD y llego {valor!r}", campo=variable.nombre
            ) from exc
    if variable.tipo == "entero":
        try:
            return str(int(str(valor)))
        except ValueError as exc:
            raise VariableInvalida(
                f"{variable.nombre} debe ser entero y llego {valor!r}", campo=variable.nombre
            ) from exc

    texto = str(valor if valor is not None else "").strip()
    if not texto:
        raise VariableInvalida(f"{variable.nombre} llego vacia", campo=variable.nombre)
    return texto


def _existe_destinatario(destinatario_id: str, catalogo: Catalogo) -> bool:
    return destinatario_id in catalogo.clientes or destinatario_id in catalogo.operadores


def render(
    plantilla_id: str,
    variables: dict[str, object],
    *,
    destinatario_id: str,
    catalogo: Catalogo,
    plantillas: CatalogoPlantillas | None = None,
) -> Mensaje:
    """Rinde la plantilla. Si algo no cuadra, levanta: un aviso a medias no se manda."""
    plantillas = plantillas or cargar_plantillas()
    plantilla = plantillas.plantilla(plantilla_id)

    if not _existe_destinatario(destinatario_id, catalogo):
        raise DestinatarioDesconocido(
            f"{destinatario_id} no esta en svc-masterdata: no se envia a un destinatario suelto",
            campo="destinatario_id",
        )

    sobran = set(variables) - set(plantilla.variables)
    if sobran:
        # Una variable de más suele ser un error de nombre en una que sí hacía falta.
        raise VariableInvalida(
            f"la plantilla {plantilla_id} no declara {', '.join(sorted(sobran))}", campo="variables"
        )

    valores: dict[str, str] = {}
    for nombre, variable in plantilla.variables.items():
        if nombre not in variables or variables[nombre] is None:
            if variable.obligatoria:
                raise VariableInvalida(
                    f"falta la variable {nombre} de la plantilla {plantilla_id}", campo=nombre
                )
            valores[nombre] = ""
            continue
        valores[nombre] = _convertir(variables[nombre], variable)

    return Mensaje(
        plantilla_id=plantilla.plantilla_id,
        canal=plantilla.canal,
        destinatario_id=destinatario_id,
        asunto=plantilla.asunto.format(**valores),
        texto=plantilla.texto.format(**valores),
        plantillas_version=plantillas.version,
        aprobada=plantillas.aprobadas,
        variables=valores,
        generado=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@dataclass(frozen=True)
class Envio:
    mensaje: Mensaje
    estado: str          # registrado_sin_canal | registrado_para_envio_humano | enviado
    trace_id: str = ""

    def as_dict(self) -> dict[str, object]:
        return {"estado": self.estado, "trace_id": self.trace_id, **self.mensaje.as_dict()}


def enviar(
    mensaje: Mensaje,
    *,
    runlog=None,
    trace_id: str = "",
    plantillas: CatalogoPlantillas | None = None,
) -> Envio:
    """Deja el envío registrado en `svc-runlog`. Sin canal contratado, no finge haber enviado."""
    plantillas = plantillas or cargar_plantillas()
    if mensaje.canal not in plantillas.canales:
        raise CanalNoDisponible(f"canal desconocido: {mensaje.canal!r}", campo="canal")

    # "enviado" solo si el canal esta activo Y de verdad sale por si solo. Con el canal
    # `bitacora` el mensaje queda escrito y lo manda una persona: decir "enviado" ahi seria
    # exactamente la clase de mentira que despues nadie detecta.
    if not plantillas.canal_activo(mensaje.canal):
        estado = "registrado_sin_canal"
    elif plantillas.entrega_de(mensaje.canal) == "externa":
        estado = "enviado"
    else:
        estado = "registrado_para_envio_humano"

    if runlog is not None and trace_id:
        runlog.registrar_paso(
            trace_id,
            actor="svc-notify",
            tipo="llamada_servicio",
            resultado="ok",
            entradas={"plantilla": mensaje.plantilla_id, "destinatario": mensaje.destinatario_id},
            salidas={"estado": estado, "asunto": mensaje.asunto},
            versiones={"plantillas_version": mensaje.plantillas_version},
        )

    return Envio(mensaje=mensaje, estado=estado, trace_id=trace_id)
