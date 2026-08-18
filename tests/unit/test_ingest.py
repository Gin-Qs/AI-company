"""svc-ingest: normalizacion, cuarentena de filas malas y derivaciones exactas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.ingest import (
    normalizar_banco,
    normalizar_diesel,
    normalizar_gps,
    normalizar_viajes,
    precio_diesel_promedio,
)
from services.ingest.normalizador import CODIGO_INCONSISTENTE, CODIGO_REFERENCIA


def test_banco_cargo_abono_a_monto_firmado():
    """Cargo y abono se colapsan en un monto con signo: ingreso positivo, egreso negativo."""
    filas = [
        {"Fecha": "04/05/2026", "Concepto": "Deposito CL-01", "Cargo": "", "Abono": "26,500.00", "Referencia": "A1"},
        {"Fecha": "05/05/2026", "Concepto": "Diesel", "Cargo": "9,538.00", "Abono": "", "Referencia": "A2"},
    ]

    resultado = normalizar_banco(filas, cuenta_default="0011234567")

    assert [m.monto_mxn for m in resultado.registros] == [Decimal("26500.00"), Decimal("-9538.00")]
    assert [m.tipo for m in resultado.registros] == ["ingreso", "egreso"]
    assert resultado.registros[0].cuenta == "0011234567"
    assert resultado.ok


def test_banco_fila_invalida_no_tumba_lote():
    """Un renglon roto se cuarentena con codigo; los demas pasan. Un estado de cuenta no se pierde por uno."""
    filas = [
        {"fecha": "04/05/2026", "concepto": "Bueno", "abono": "1000"},
        {"fecha": "no es fecha", "concepto": "Fecha rota", "abono": "500"},
        {"fecha": "06/05/2026", "concepto": "Sin importe"},
        {"fecha": "07/05/2026", "concepto": "En cero", "abono": "0"},
        {"fecha": "08/05/2026", "concepto": "Bueno tambien", "cargo": "250"},
    ]

    resultado = normalizar_banco(filas)

    assert len(resultado.registros) == 2
    assert [r.codigo for r in resultado.rechazos] == ["ING-INVALIDO", "ING-CAMPO-FALTANTE", "ING-INVALIDO"]
    assert resultado.tasa_rechazo_pct == Decimal("60.00")
    assert not resultado.ok


def test_dedupe_por_clave_natural():
    """El mismo movimiento cargado dos veces se cuenta una vez, y el duplicado se reporta."""
    fila = {"fecha": "2026-05-04", "concepto": "Deposito", "abono": "1000", "referencia": "A1", "cuenta": "001"}

    resultado = normalizar_banco([fila, dict(fila), {**fila, "referencia": "A2"}])

    assert len(resultado.registros) == 2
    assert resultado.duplicados == 1


def test_diesel_deriva_precio_por_litro(catalogo):
    """Con litros e importe, el precio se deriva por division exacta y se cuenta como derivado."""
    filas = [{"ticket": "TK-1", "fecha": "2026-05-05", "unidad": "U-01", "litros": "380", "importe": "9538.00"}]

    resultado = normalizar_diesel(filas, catalogo=catalogo)

    carga = resultado.registros[0]
    assert carga.precio_mxn_litro == Decimal("25.1000")
    assert carga.importe_mxn == Decimal("9538.00")
    assert resultado.derivados == 1


def test_diesel_inconsistente_se_rechaza(catalogo):
    """Litros x precio que no cuadra con el importe es un ticket mal capturado, no un dato a corregir."""
    filas = [
        {"ticket": "TK-1", "fecha": "2026-05-05", "unidad": "U-01", "litros": "380", "precio": "25.10", "importe": "9538.00"},
        {"ticket": "TK-2", "fecha": "2026-05-06", "unidad": "U-01", "litros": "380", "precio": "25.10", "importe": "5000.00"},
    ]

    resultado = normalizar_diesel(filas, catalogo=catalogo)

    assert len(resultado.registros) == 1
    assert resultado.rechazos[0].codigo == CODIGO_INCONSISTENTE
    assert resultado.derivados == 0


def test_diesel_unidad_fuera_de_catalogo(catalogo):
    filas = [{"ticket": "TK-9", "fecha": "2026-05-05", "unidad": "U-99", "litros": "100", "precio": "25.00"}]

    resultado = normalizar_diesel(filas, catalogo=catalogo)

    assert resultado.registros == []
    assert resultado.rechazos[0].codigo == CODIGO_REFERENCIA


def test_gps_km_por_haversine():
    """Sin columna de distancia, los km salen de sumar haversines entre puntos consecutivos."""
    filas = [
        {"unit_id": "U-01", "trip_id": "T-01", "timestamp": "2026-06-01 08:00", "lat": "25.6866", "lon": "-100.3161"},
        {"unit_id": "U-01", "trip_id": "T-01", "timestamp": "2026-06-01 12:00", "lat": "24.0277", "lon": "-104.6532"},
        {"unit_id": "U-02", "trip_id": "T-02", "timestamp": "2026-06-01 09:00", "km": "540"},
    ]

    resultado = normalizar_gps(filas)
    por_viaje = {r.trip_id: r for r in resultado.registros}

    # Monterrey a Durango en linea recta ronda los 460 km.
    assert Decimal("440") < por_viaje["T-01"].km_recorridos < Decimal("480")
    assert por_viaje["T-01"].puntos == 2
    assert por_viaje["T-02"].km_recorridos == Decimal("540.00")


def test_gps_un_solo_punto_no_produce_distancia():
    filas = [{"unit_id": "U-01", "trip_id": "T-01", "timestamp": "2026-06-01 08:00", "lat": "25.6", "lon": "-100.3"}]

    resultado = normalizar_gps(filas)

    assert resultado.registros == []
    assert resultado.rechazos[0].codigo == CODIGO_INCONSISTENTE


def test_viajes_referencias_desconocidas_se_rechazan(catalogo):
    """Un viaje que apunta a una ruta o unidad que no existe no entra al costeo."""
    filas = [
        {
            "trip_id": "T-01", "route_id": "R-01", "unit_id": "U-01", "operador_id": "OP-KM",
            "cliente_id": "CL-01", "fecha_inicio": "2026-06-01", "fecha_fin": "2026-06-02", "ingreso": "30000",
        },
        {
            "trip_id": "T-02", "route_id": "R-99", "unit_id": "U-01", "operador_id": "OP-KM",
            "cliente_id": "CL-01", "fecha_inicio": "2026-06-03", "fecha_fin": "2026-06-04", "ingreso": "20000",
        },
        {
            "trip_id": "T-03", "route_id": "R-01", "unit_id": "U-01", "operador_id": "OP-KM",
            "cliente_id": "", "fecha_inicio": "2026-06-05", "fecha_fin": "2026-06-06", "ingreso": "20000",
        },
    ]

    resultado = normalizar_viajes(filas, catalogo=catalogo)

    assert [v.trip_id for v in resultado.registros] == ["T-01"]
    assert {r.codigo for r in resultado.rechazos} == {CODIGO_REFERENCIA}
    assert resultado.registros[0].dias == 2


def test_viajes_solo_cerrados_ignora_los_abiertos(catalogo):
    filas = [
        {
            "trip_id": "T-01", "route_id": "R-01", "unit_id": "U-01", "operador_id": "OP-KM", "cliente_id": "CL-01",
            "fecha_inicio": "2026-06-01", "fecha_fin": "2026-06-02", "ingreso": "30000", "estatus": "en ruta",
        },
    ]

    assert normalizar_viajes(filas, catalogo=catalogo, solo_cerrados=True).registros == []
    assert len(normalizar_viajes(filas, catalogo=catalogo).registros) == 1


def test_viajes_fechas_invertidas_se_rechazan(catalogo):
    filas = [
        {
            "trip_id": "T-01", "route_id": "R-01", "unit_id": "U-01", "operador_id": "OP-KM", "cliente_id": "CL-01",
            "fecha_inicio": "2026-06-05", "fecha_fin": "2026-06-01", "ingreso": "30000",
        },
    ]

    resultado = normalizar_viajes(filas, catalogo=catalogo)

    assert resultado.registros == []
    assert "fin anterior" in resultado.rechazos[0].motivo


def test_precio_diesel_promedio_ponderado(catalogo):
    """Ponderado por litros, no promedio simple de precios: 400 L caros pesan mas que 100 L baratos."""
    filas = [
        {"ticket": "TK-1", "fecha": "2026-05-05", "unidad": "U-01", "litros": "100", "precio": "20.00"},
        {"ticket": "TK-2", "fecha": "2026-05-20", "unidad": "U-01", "litros": "400", "precio": "25.00"},
        {"ticket": "TK-3", "fecha": "2026-06-05", "unidad": "U-01", "litros": "100", "precio": "30.00"},
    ]
    cargas = normalizar_diesel(filas, catalogo=catalogo).registros

    todo = precio_diesel_promedio(cargas)
    mayo = precio_diesel_promedio(cargas, desde=date(2026, 5, 1), hasta=date(2026, 5, 31))

    assert mayo == Decimal("24.0000")  # (2000 + 10000) / 500
    assert todo == Decimal("25.0000")  # (2000 + 10000 + 3000) / 600
    assert precio_diesel_promedio([]) is None


def test_encabezados_con_acentos_y_mayusculas():
    """Los CSV reales llegan con 'Fecha Operación' y con BOM. El servicio no se entera."""
    filas = [{"Fecha Operación": "2026-05-04", "Descripción": "Deposito", "Depósito": "1,000.00"}]

    resultado = normalizar_banco(filas)

    assert resultado.registros[0].monto_mxn == Decimal("1000.00")
    assert resultado.registros[0].concepto == "Deposito"
