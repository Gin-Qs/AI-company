"""svc-cfdi-validate: estructura, catálogo y aritmética. Ni corrige, ni timbra, ni opina."""

from __future__ import annotations

import pytest

from services.cfdi_validate import XMLIlegible, cargar_catalogos, validar_cfdi

RFC_CLIENTE = "ANO910415AB1"


@pytest.fixture
def cfdi(raiz) -> str:
    return (raiz / "tests" / "fixtures" / "cfdi_valido.xml").read_text(encoding="utf-8")


def test_cfdi_valido_pasa(cfdi):
    dictamen = validar_cfdi(cfdi, rfc_receptor_esperado=RFC_CLIENTE)

    assert dictamen.ok
    assert dictamen.cfdi_version == "4.0"
    assert dictamen.con_carta_porte


def test_estructura_incompleta_se_rechaza(cfdi):
    """Sin Receptor no hay comprobante. Lo atrapa antes de llegar al PAC."""
    sin_receptor = cfdi.replace('  <cfdi:Receptor Rfc="ANO910415AB1"', "  <!--<cfdi:Receptor Rfc=x").replace(
        'UsoCFDI="G03"/>', 'UsoCFDI="G03"/>-->'
    )

    dictamen = validar_cfdi(sin_receptor)

    assert not dictamen.ok
    assert any(h.regla == "CFDI-005" for h in dictamen.errores)


def test_lo_que_no_es_un_comprobante_no_se_dictamina():
    with pytest.raises(XMLIlegible):
        validar_cfdi("esto no es xml")

    otro = validar_cfdi("<Pedido><Linea/></Pedido>")

    assert not otro.ok
    assert otro.errores[0].regla == "CFDI-001"


def test_carta_porte_sin_mercancia_se_rechaza(cfdi):
    """La regla que más rechaza en la práctica: un traslado sin mercancía declarada."""
    inicio = cfdi.index("<cartaporte31:Mercancia ")
    fin = cfdi.index("</cartaporte31:Mercancia>") + len("</cartaporte31:Mercancia>")
    sin_mercancia = cfdi[:inicio] + cfdi[fin:]

    dictamen = validar_cfdi(sin_mercancia)

    assert not dictamen.ok
    assert any(h.regla == "CP-004" for h in dictamen.errores)


def test_clave_fuera_de_catalogo_se_detecta(cfdi):
    fuera = cfdi.replace('ClaveUnidad="E48"', 'ClaveUnidad="XYZ"')

    dictamen = validar_cfdi(fuera)

    assert not dictamen.ok
    assert any(h.regla == "CFDI-018" for h in dictamen.errores)


def test_el_total_que_no_cuadra_se_detecta(cfdi):
    """El error más caro y el más silencioso: la suma que nadie rehace."""
    descuadrado = cfdi.replace('Total="29680.00"', 'Total="30000.00"')

    dictamen = validar_cfdi(descuadrado)

    assert any(h.regla == "CFDI-022" for h in dictamen.errores)


def test_el_importe_del_concepto_es_cantidad_por_valor_unitario(cfdi):
    mal = cfdi.replace('ValorUnitario="26500.00"', 'ValorUnitario="26000.00"')

    dictamen = validar_cfdi(mal)

    assert any(h.regla == "CFDI-020" for h in dictamen.errores)


def test_receptor_no_coincide_con_el_cliente_del_viaje(cfdi):
    """Facturarle al cliente equivocado es un problema con dos cobranzas y una cancelación."""
    dictamen = validar_cfdi(cfdi, rfc_receptor_esperado="CBA050822KJ7")

    assert not dictamen.ok
    assert any(h.regla == "CFDI-030" for h in dictamen.errores)


def test_el_dictamen_declara_la_version_de_catalogo(cfdi):
    """Sin esa versión el dictamen no se puede repetir dentro de seis meses."""
    catalogos = cargar_catalogos()
    dictamen = validar_cfdi(cfdi, catalogos=catalogos, rfc_receptor_esperado=RFC_CLIENTE)

    assert dictamen.catalogo_version == catalogos.version
    assert dictamen.as_dict()["catalogo_version"] == catalogos.version


def test_el_dictamen_no_se_presenta_como_validacion_xsd(cfdi):
    """La honestidad del servicio: dice lo que no hace, en la salida, no sólo en el README."""
    dictamen = validar_cfdi(cfdi, rfc_receptor_esperado=RFC_CLIENTE)

    assert dictamen.as_dict()["valida_xsd"] is False
    assert not dictamen.catalogo_completo
    assert any(h.regla == "CFDI-000" for h in dictamen.dictamen.advertencias)


def test_un_traslado_sin_complemento_se_detecta_cuando_se_exige(cfdi):
    inicio = cfdi.index("  <cfdi:Complemento>")
    fin = cfdi.index("</cfdi:Complemento>") + len("</cfdi:Complemento>")
    sin_complemento = cfdi[:inicio] + cfdi[fin:]

    assert validar_cfdi(sin_complemento, exige_carta_porte=True).errores[0].regla == "CP-001"
    assert validar_cfdi(sin_complemento, rfc_receptor_esperado=RFC_CLIENTE).ok
