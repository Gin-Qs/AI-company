"""svc-ingest - normalizacion de origenes heterogeneos.

Dos reglas gobiernan este modulo:

1. **Una fila mala no tumba el lote.** Se cuarentena con un codigo de motivo y
   el proceso sigue. Un estado de cuenta de 800 movimientos no puede fallar
   entero por un renglon de comisiones sin referencia.
2. **Nada se adivina en silencio.** Lo que se deriva (el precio por litro que
   no venia en el ticket) se deriva por aritmetica exacta y se marca; lo que
   no se puede derivar se rechaza.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Sequence

from services.common.errors import ErrorDeValidacion
from services.common.money import cantidad, cuota, mxn
from services.ingest.registros import CargaDiesel, MovimientoBancario, RecorridoGPS, Viaje
from services.masterdata.catalogo import Catalogo
from services.masterdata.models import FORMATOS_FECHA, fecha as parse_fecha

TOLERANCIA_DIESEL_PCT = Decimal("1.0")  # 1% entre litros x precio e importe del ticket
TOLERANCIA_DIESEL_MXN = Decimal("2.00")  # o dos pesos, lo que sea mayor: el ticket redondea


@dataclass(frozen=True)
class Rechazo:
    """Una fila en cuarentena. Se reporta, no se descarta en silencio."""

    fila: int
    codigo: str
    motivo: str
    datos: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {"fila": self.fila, "codigo": self.codigo, "motivo": self.motivo, "datos": self.datos}


@dataclass
class ResultadoIngesta:
    origen: str
    registros: list = field(default_factory=list)
    rechazos: list[Rechazo] = field(default_factory=list)
    duplicados: int = 0
    derivados: int = 0

    @property
    def ok(self) -> bool:
        return not self.rechazos

    @property
    def tasa_rechazo_pct(self) -> Decimal:
        total = len(self.registros) + len(self.rechazos) + self.duplicados
        if total == 0:
            return Decimal("0.00")
        return ((Decimal(len(self.rechazos)) / Decimal(total)) * 100).quantize(Decimal("0.01"))

    def resumen(self) -> dict[str, object]:
        return {
            "origen": self.origen,
            "aceptados": len(self.registros),
            "rechazados": len(self.rechazos),
            "duplicados": self.duplicados,
            "derivados": self.derivados,
            "tasa_rechazo_pct": str(self.tasa_rechazo_pct),
        }


# --- utilidades de lectura de filas --------------------------------------

CODIGO_FALTANTE = "ING-CAMPO-FALTANTE"
CODIGO_INVALIDO = "ING-INVALIDO"
CODIGO_DUPLICADO = "ING-DUPLICADO"
CODIGO_REFERENCIA = "ING-REF-DESCONOCIDA"
CODIGO_INCONSISTENTE = "ING-INCONSISTENTE"


def normalizar_encabezados(fila: dict) -> dict[str, str]:
    """Minusculas, sin espacios de sobra y sin acentos: los CSV reales varian en las tres cosas."""
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return {
        str(clave or "").strip().lower().translate(tabla).replace("  ", " "): ("" if valor is None else str(valor))
        for clave, valor in fila.items()
    }


def valor(fila: dict[str, str], alias: Sequence[str]) -> str:
    for nombre in alias:
        if nombre in fila and str(fila[nombre]).strip():
            return str(fila[nombre]).strip()
    return ""


def marca_de_tiempo(texto: str, *, campo: str = "timestamp") -> datetime:
    """Fecha con hora. Si el origen solo trae fecha, la hora es 00:00."""
    limpio = str(texto or "").strip().replace("T", " ")
    if not limpio:
        raise ErrorDeValidacion("marca de tiempo vacia", campo=campo)
    for formato_fecha in FORMATOS_FECHA:
        for sufijo in (" %H:%M:%S", " %H:%M", ""):
            try:
                return datetime.strptime(limpio, formato_fecha + sufijo)
            except ValueError:
                continue
    raise ErrorDeValidacion(f"marca de tiempo no reconocida: {texto!r}", campo=campo)


def km_entre(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine sobre radio medio terrestre. Aproxima la distancia real por carretera por debajo."""
    radio = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))


# --- banco ----------------------------------------------------------------

ALIAS_BANCO = {
    "fecha": ("fecha", "fecha operacion", "fecha de operacion", "f. oper", "fecha movimiento"),
    "concepto": ("concepto", "descripcion", "detalle", "referencia amplia"),
    "monto": ("monto", "importe", "monto mxn"),
    "cargo": ("cargo", "retiro", "retiros", "debito"),
    "abono": ("abono", "deposito", "depositos", "credito"),
    "cuenta": ("cuenta", "no. cuenta", "numero de cuenta", "clabe"),
    "referencia": ("referencia", "ref", "folio", "no. movimiento"),
}


def normalizar_banco(
    filas: Iterable[dict],
    *,
    cuenta_default: str = "",
    origen: str = "banco",
) -> ResultadoIngesta:
    """Estados de cuenta. Acepta columna unica de monto o el par cargo/abono."""
    resultado = ResultadoIngesta(origen=origen)
    vistos: set[tuple] = set()

    for numero, cruda in enumerate(filas, start=2):
        fila = normalizar_encabezados(cruda)
        try:
            dia = parse_fecha(valor(fila, ALIAS_BANCO["fecha"]), campo="fecha")
        except ErrorDeValidacion as exc:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
            continue

        texto_monto = valor(fila, ALIAS_BANCO["monto"])
        texto_cargo = valor(fila, ALIAS_BANCO["cargo"])
        texto_abono = valor(fila, ALIAS_BANCO["abono"])
        try:
            if texto_monto:
                monto = mxn(texto_monto, campo="monto")
            elif texto_abono or texto_cargo:
                monto = mxn(texto_abono or 0, campo="abono") - abs(mxn(texto_cargo or 0, campo="cargo"))
            else:
                resultado.rechazos.append(
                    Rechazo(numero, CODIGO_FALTANTE, "sin monto, cargo ni abono", fila)
                )
                continue
        except ErrorDeValidacion as exc:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
            continue

        if monto == 0:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "movimiento en cero", fila))
            continue

        movimiento = MovimientoBancario(
            fecha=dia,
            concepto=valor(fila, ALIAS_BANCO["concepto"]),
            monto_mxn=monto,
            cuenta=valor(fila, ALIAS_BANCO["cuenta"]) or cuenta_default,
            referencia=valor(fila, ALIAS_BANCO["referencia"]),
            origen=origen,
        )
        if movimiento.clave_dedupe in vistos:
            resultado.duplicados += 1
            continue
        vistos.add(movimiento.clave_dedupe)
        resultado.registros.append(movimiento)

    return resultado


# --- diesel ---------------------------------------------------------------

ALIAS_DIESEL = {
    "ticket": ("ticket_id", "ticket", "folio", "no. ticket", "comprobante"),
    "fecha": ("fecha", "fecha carga", "fecha de carga"),
    "unidad": ("unit_id", "unidad", "economico", "no. economico", "tracto"),
    "litros": ("litros", "lts", "cantidad", "volumen"),
    "precio": ("precio_mxn_litro", "precio", "precio litro", "precio por litro", "precio unitario", "p.u."),
    "importe": ("importe_mxn", "importe", "total", "monto"),
    "odometro": ("odometro_km", "odometro", "km", "kilometraje"),
    "estacion": ("estacion", "gasolinera", "proveedor", "estacion de servicio"),
}


def normalizar_diesel(
    filas: Iterable[dict],
    *,
    catalogo: Catalogo | None = None,
    origen: str = "diesel",
) -> ResultadoIngesta:
    """Tickets de diesel. Deriva el tercer valor cuando faltan litros, precio o importe."""
    resultado = ResultadoIngesta(origen=origen)
    vistos: set[tuple] = set()

    for numero, cruda in enumerate(filas, start=2):
        fila = normalizar_encabezados(cruda)
        unidad = valor(fila, ALIAS_DIESEL["unidad"])
        if not unidad:
            resultado.rechazos.append(Rechazo(numero, CODIGO_FALTANTE, "sin unidad", fila))
            continue
        if catalogo is not None and unidad not in catalogo.unidades:
            resultado.rechazos.append(
                Rechazo(numero, CODIGO_REFERENCIA, f"unidad fuera del catalogo: {unidad}", fila)
            )
            continue

        try:
            dia = parse_fecha(valor(fila, ALIAS_DIESEL["fecha"]), campo="fecha")
            litros = cuota(valor(fila, ALIAS_DIESEL["litros"]) or 0, campo="litros")
            precio = cuota(valor(fila, ALIAS_DIESEL["precio"]) or 0, campo="precio")
            importe = mxn(valor(fila, ALIAS_DIESEL["importe"]) or 0, campo="importe")
            odometro_texto = valor(fila, ALIAS_DIESEL["odometro"])
            odometro = cantidad(odometro_texto, campo="odometro") if odometro_texto else None
        except ErrorDeValidacion as exc:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
            continue

        presentes = sum(1 for x in (litros, precio, importe) if x > 0)
        if presentes < 2:
            resultado.rechazos.append(
                Rechazo(numero, CODIGO_FALTANTE, "se necesitan al menos dos de litros, precio e importe", fila)
            )
            continue

        if litros <= 0:
            litros = cuota(importe / precio, campo="litros")
            resultado.derivados += 1
        elif precio <= 0:
            precio = cuota(importe / litros, campo="precio")
            resultado.derivados += 1
        elif importe <= 0:
            importe = mxn(litros * precio, campo="importe")
            resultado.derivados += 1
        else:
            calculado = litros * precio
            desviacion = abs(calculado - importe)
            tolerancia = max(importe * TOLERANCIA_DIESEL_PCT / 100, TOLERANCIA_DIESEL_MXN)
            if desviacion > tolerancia:
                resultado.rechazos.append(
                    Rechazo(
                        numero,
                        CODIGO_INCONSISTENTE,
                        f"litros x precio = {calculado:.2f} no cuadra con importe {importe:.2f}",
                        fila,
                    )
                )
                continue

        carga = CargaDiesel(
            ticket_id=valor(fila, ALIAS_DIESEL["ticket"]) or f"{unidad}-{dia.isoformat()}-{numero}",
            fecha=dia,
            unit_id=unidad,
            litros=litros,
            precio_mxn_litro=precio,
            importe_mxn=importe,
            odometro_km=odometro,
            estacion=valor(fila, ALIAS_DIESEL["estacion"]),
            origen=origen,
        )
        if carga.clave_dedupe in vistos:
            resultado.duplicados += 1
            continue
        vistos.add(carga.clave_dedupe)
        resultado.registros.append(carga)

    return resultado


# --- GPS ------------------------------------------------------------------

ALIAS_GPS = {
    "unidad": ("unit_id", "unidad", "economico", "movil", "vehiculo"),
    "viaje": ("trip_id", "viaje", "folio viaje"),
    "timestamp": ("timestamp", "fecha", "fecha hora", "fecha y hora", "hora"),
    "lat": ("lat", "latitud", "latitude"),
    "lon": ("lon", "lng", "longitud", "longitude"),
    "km": ("km", "km_recorridos", "distancia", "distancia km", "odometro delta"),
}


def normalizar_gps(filas: Iterable[dict], *, origen: str = "gps") -> ResultadoIngesta:
    """Puntos GPS agregados a km por unidad y viaje.

    Si el proveedor ya exporta distancia por viaje, se toma esa columna. Si
    solo hay posiciones, se suman haversines entre puntos consecutivos: el
    resultado subestima la distancia por carretera, y por eso se compara
    contra los km de la ruta en lugar de sustituirlos.
    """
    resultado = ResultadoIngesta(origen=origen)
    puntos: dict[tuple[str, str | None], list[tuple[datetime, float, float]]] = {}
    resumidos: dict[tuple[str, str | None], list] = {}

    for numero, cruda in enumerate(filas, start=2):
        fila = normalizar_encabezados(cruda)
        unidad = valor(fila, ALIAS_GPS["unidad"])
        if not unidad:
            resultado.rechazos.append(Rechazo(numero, CODIGO_FALTANTE, "sin unidad", fila))
            continue
        viaje = valor(fila, ALIAS_GPS["viaje"]) or None
        try:
            momento = marca_de_tiempo(valor(fila, ALIAS_GPS["timestamp"]))
        except ErrorDeValidacion as exc:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
            continue

        texto_km = valor(fila, ALIAS_GPS["km"])
        if texto_km:
            try:
                km = cantidad(texto_km, campo="km")
            except ErrorDeValidacion as exc:
                resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
                continue
            if km < 0:
                resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "distancia negativa", fila))
                continue
            resumidos.setdefault((unidad, viaje), []).append((momento, km))
            continue

        try:
            lat = float(valor(fila, ALIAS_GPS["lat"]))
            lon = float(valor(fila, ALIAS_GPS["lon"]))
        except ValueError:
            resultado.rechazos.append(Rechazo(numero, CODIGO_FALTANTE, "sin distancia ni coordenadas validas", fila))
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "coordenada fuera de rango", fila))
            continue
        puntos.setdefault((unidad, viaje), []).append((momento, lat, lon))

    for (unidad, viaje), muestras in sorted(resumidos.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        muestras.sort(key=lambda m: m[0])
        total = sum((m[1] for m in muestras), Decimal(0))
        resultado.registros.append(
            RecorridoGPS(
                unit_id=unidad,
                trip_id=viaje,
                fecha_inicio=muestras[0][0].date(),
                fecha_fin=muestras[-1][0].date(),
                km_recorridos=total.quantize(Decimal("0.01")),
                puntos=len(muestras),
                origen=origen,
            )
        )

    for (unidad, viaje), muestras in sorted(puntos.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        muestras.sort(key=lambda m: m[0])
        if len(muestras) < 2:
            resultado.rechazos.append(
                Rechazo(0, CODIGO_INCONSISTENTE, f"un solo punto GPS para {unidad}/{viaje}: no hay distancia", {})
            )
            continue
        total = 0.0
        for (_, lat1, lon1), (_, lat2, lon2) in zip(muestras, muestras[1:]):
            total += km_entre(lat1, lon1, lat2, lon2)
        resultado.registros.append(
            RecorridoGPS(
                unit_id=unidad,
                trip_id=viaje,
                fecha_inicio=muestras[0][0].date(),
                fecha_fin=muestras[-1][0].date(),
                km_recorridos=Decimal(str(round(total, 2))),
                puntos=len(muestras),
                origen=origen,
            )
        )

    return resultado


# --- viajes del ERP -------------------------------------------------------

ALIAS_VIAJE = {
    "trip": ("trip_id", "viaje", "folio", "no. viaje", "orden"),
    "ruta": ("route_id", "ruta", "id ruta"),
    "unidad": ("unit_id", "unidad", "economico", "tracto"),
    "operador": ("operador_id", "operador", "chofer", "conductor"),
    "cliente": ("cliente_id", "cliente", "id cliente"),
    "inicio": ("fecha_inicio", "fecha inicio", "salida", "fecha salida"),
    "fin": ("fecha_fin", "fecha fin", "llegada", "fecha llegada", "fecha entrega"),
    "ingreso": ("ingreso_facturado_mxn", "ingreso", "flete", "facturado", "importe", "venta"),
    "km": ("km_recorridos", "km", "kilometros", "distancia"),
    "estatus": ("estatus", "estado", "status"),
}

ESTATUS_VALIDOS = ("cerrado", "abierto", "cancelado", "en_ruta")


def normalizar_viajes(
    filas: Iterable[dict],
    *,
    catalogo: Catalogo | None = None,
    origen: str = "erp",
    solo_cerrados: bool = False,
) -> ResultadoIngesta:
    """Viajes del ERP. Con catalogo, valida que ruta, unidad, operador y cliente existan."""
    resultado = ResultadoIngesta(origen=origen)
    vistos: set[tuple] = set()

    for numero, cruda in enumerate(filas, start=2):
        fila = normalizar_encabezados(cruda)
        trip = valor(fila, ALIAS_VIAJE["trip"])
        if not trip:
            resultado.rechazos.append(Rechazo(numero, CODIGO_FALTANTE, "sin folio de viaje", fila))
            continue

        try:
            inicio = parse_fecha(valor(fila, ALIAS_VIAJE["inicio"]), campo="fecha_inicio")
            texto_fin = valor(fila, ALIAS_VIAJE["fin"])
            fin = parse_fecha(texto_fin, campo="fecha_fin") if texto_fin else inicio
            ingreso = mxn(valor(fila, ALIAS_VIAJE["ingreso"]) or 0, campo="ingreso_facturado_mxn")
            texto_km = valor(fila, ALIAS_VIAJE["km"])
            km = cantidad(texto_km, campo="km_recorridos") if texto_km else None
        except ErrorDeValidacion as exc:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, exc.mensaje, fila))
            continue

        if fin < inicio:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "fecha de fin anterior al inicio", fila))
            continue
        if ingreso < 0:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "ingreso negativo", fila))
            continue
        if km is not None and km <= 0:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, "km recorridos no positivos", fila))
            continue

        estatus = (valor(fila, ALIAS_VIAJE["estatus"]) or "cerrado").lower().replace(" ", "_")
        if estatus not in ESTATUS_VALIDOS:
            resultado.rechazos.append(Rechazo(numero, CODIGO_INVALIDO, f"estatus desconocido: {estatus}", fila))
            continue
        if solo_cerrados and estatus != "cerrado":
            continue

        viaje = Viaje(
            trip_id=trip,
            route_id=valor(fila, ALIAS_VIAJE["ruta"]),
            unit_id=valor(fila, ALIAS_VIAJE["unidad"]),
            operador_id=valor(fila, ALIAS_VIAJE["operador"]),
            cliente_id=valor(fila, ALIAS_VIAJE["cliente"]),
            fecha_inicio=inicio,
            fecha_fin=fin,
            ingreso_facturado_mxn=ingreso,
            km_recorridos=km,
            estatus=estatus,
            origen=origen,
        )

        faltante = _referencias_invalidas(viaje, catalogo)
        if faltante:
            resultado.rechazos.append(Rechazo(numero, CODIGO_REFERENCIA, faltante, fila))
            continue

        if viaje.clave_dedupe in vistos:
            resultado.duplicados += 1
            continue
        vistos.add(viaje.clave_dedupe)
        resultado.registros.append(viaje)

    return resultado


def _referencias_invalidas(viaje: Viaje, catalogo: Catalogo | None) -> str:
    obligatorios = {
        "route_id": viaje.route_id,
        "unit_id": viaje.unit_id,
        "operador_id": viaje.operador_id,
        "cliente_id": viaje.cliente_id,
    }
    vacios = [campo for campo, valor_campo in obligatorios.items() if not valor_campo]
    if vacios:
        return f"referencias vacias: {', '.join(vacios)}"
    if catalogo is None:
        return ""
    indices = {
        "route_id": (catalogo.rutas, viaje.route_id),
        "unit_id": (catalogo.unidades, viaje.unit_id),
        "operador_id": (catalogo.operadores, viaje.operador_id),
        "cliente_id": (catalogo.clientes, viaje.cliente_id),
    }
    desconocidos = [f"{campo}={clave}" for campo, (indice, clave) in indices.items() if clave not in indice]
    return f"fuera del catalogo: {', '.join(desconocidos)}" if desconocidos else ""


def precio_diesel_promedio(cargas: Sequence[CargaDiesel], *, desde: date | None = None, hasta: date | None = None) -> Decimal | None:
    """Precio por litro ponderado por litros del periodo.

    Es la entrada `fuel_price` de svc-costing cuando el viaje no trae su
    propio ticket: promedio real de lo que se pago, no el precio de lista.
    """
    seleccion = [
        c
        for c in cargas
        if (desde is None or c.fecha >= desde) and (hasta is None or c.fecha <= hasta)
    ]
    litros = sum((c.litros for c in seleccion), Decimal(0))
    if litros <= 0:
        return None
    importe = sum((c.importe_mxn for c in seleccion), Decimal(0))
    return cuota(importe / litros, campo="precio_diesel_mxn_litro")
