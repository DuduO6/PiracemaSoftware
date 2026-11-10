from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import xml.etree.ElementTree as ET


MONEY = Decimal("0.01")
WEIGHT = Decimal("0.001")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if _local_name(child.tag) == name]


def _first(node: ET.Element, name: str) -> ET.Element | None:
    return next(iter(_children(node, name)), None)


def _direct(node: ET.Element | None, name: str) -> ET.Element | None:
    if node is None:
        return None
    return next((child for child in node if _local_name(child.tag) == name), None)


def _text(node: ET.Element | None, name: str, default: str = "") -> str:
    found = _direct(node, name)
    return (found.text or "").strip() if found is not None else default


def _decimal(value: str) -> Decimal:
    try:
        return Decimal((value or "0").replace(",", ".").strip())
    except InvalidOperation:
        return Decimal("0")


def _money(value: Decimal) -> str:
    return f"{value.quantize(MONEY, rounding=ROUND_HALF_UP):.2f}"


def _weight(value: Decimal) -> str:
    return f"{value.quantize(WEIGHT, rounding=ROUND_HALF_UP):.3f}"


def _parse_cte(inf: ET.Element) -> dict:
    ide = _direct(inf, "ide")
    rem = _direct(inf, "rem")
    dest = _direct(inf, "dest")
    ender_rem = _direct(rem, "enderReme")
    ender_dest = _direct(dest, "enderDest")
    inf_carga = _first(inf, "infCarga")

    origem_uf = _text(ide, "UFIni") or _text(ender_rem, "UF")
    destino_uf = _text(ide, "UFFim") or _text(ender_dest, "UF")
    origem_cidade = _text(ide, "xMunIni") or _text(ender_rem, "xMun")
    destino_cidade = _text(ide, "xMunFim") or _text(ender_dest, "xMun")
    valor = _decimal(_text(inf_carga, "vCarga"))

    peso_ton = Decimal("0")
    for inf_q in _children(inf_carga, "infQ") if inf_carga is not None else []:
        medida = _text(inf_q, "tpMed").upper()
        quantidade = _decimal(_text(inf_q, "qCarga"))
        unidade = _text(inf_q, "cUnid")
        if quantidade <= 0 or "PESO" not in medida:
            continue
        peso_ton = quantidade if unidade == "02" else quantidade / Decimal("1000")
        break

    return {
        "tipo_documento": "CT-e",
        "uf_origem": origem_uf,
        "uf_destino": destino_uf,
        "cidade_origem": origem_cidade,
        "cidade_destino": destino_cidade,
        "valor_carga": _money(valor),
        "peso_toneladas": _weight(peso_ton),
    }


def _parse_nfe(inf: ET.Element) -> dict:
    emit = _direct(inf, "emit")
    dest = _direct(inf, "dest")
    ender_emit = _direct(emit, "enderEmit")
    ender_dest = _direct(dest, "enderDest")
    total = _direct(inf, "total")
    icms_total = _direct(total, "ICMSTot")
    transp = _direct(inf, "transp")
    volumes = _children(transp, "vol") if transp is not None else []

    valor = _decimal(_text(icms_total, "vNF") or _text(icms_total, "vProd"))
    peso_kg = sum(
        (_decimal(_text(volume, "pesoB") or _text(volume, "pesoL")) for volume in volumes),
        Decimal("0"),
    )
    return {
        "tipo_documento": "NF-e",
        "uf_origem": _text(ender_emit, "UF"),
        "uf_destino": _text(ender_dest, "UF"),
        "cidade_origem": _text(ender_emit, "xMun"),
        "cidade_destino": _text(ender_dest, "xMun"),
        "valor_carga": _money(valor),
        "peso_toneladas": _weight(peso_kg / Decimal("1000")),
    }


def parse_documento_fiscal_xml(xml_bytes: bytes) -> dict:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("XML inválido.") from exc

    inf_cte = _first(root, "infCte")
    if inf_cte is not None:
        resultado = _parse_cte(inf_cte)
    else:
        inf_nfe = _first(root, "infNFe")
        if inf_nfe is None:
            raise ValueError("O arquivo não contém uma estrutura reconhecida de NF-e ou CT-e.")
        resultado = _parse_nfe(inf_nfe)

    if not resultado["uf_origem"] or not resultado["uf_destino"]:
        raise ValueError("Não foi possível identificar as UFs de origem e destino no XML.")
    if _decimal(resultado["valor_carga"]) <= 0:
        raise ValueError("Não foi possível identificar um valor de carga maior que zero no XML.")
    return resultado
