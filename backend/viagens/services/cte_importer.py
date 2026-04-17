from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import unicodedata
import xml.etree.ElementTree as ET

from motoristas.models import Motorista


NS = {"cte": "http://www.portalfiscal.inf.br/cte"}
TWO_PLACES = Decimal("0.01")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(normalized.upper().split())


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _find_text(node: ET.Element, path: str, default: str = "") -> str:
    found = node.find(path, NS)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _parse_decimal(value: str | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        return Decimal("0")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _title_case_city(value: str) -> str:
    lower_words = {"da", "de", "do", "das", "dos", "e"}
    parts = []
    for part in (value or "").strip().split():
        lowered = part.lower()
        parts.append(lowered if lowered in lower_words else lowered.capitalize())
    return " ".join(parts)


def _extract_driver_name(inf_cte: ET.Element) -> str:
    for obs in inf_cte.findall(".//cte:ObsCont", NS):
        x_campo = (obs.attrib.get("xCampo") or "").strip().upper()
        if "MOT" not in x_campo:
            continue
        text = _find_text(obs, "cte:xTexto")
        if not text:
            continue
        cleaned = re.split(r"-CH:|/CH:| CH:| -", text, maxsplit=1)[0].strip(" -:")
        if cleaned:
            return cleaned
    return ""


def _extract_driver_cpf(inf_cte: ET.Element) -> str:
    for obs in inf_cte.findall(".//cte:ObsCont", NS):
        x_campo = (obs.attrib.get("xCampo") or "").strip().upper()
        if x_campo != "CPFMOTORISTA":
            continue
        cpf = _digits_only(_find_text(obs, "cte:xTexto"))
        if cpf:
            return cpf
    return ""


def _resolve_tomador_name(inf_cte: ET.Element) -> str:
    toma = _find_text(inf_cte, "./cte:ide/cte:toma3/cte:toma")
    mapping = {
        "0": "rem",
        "1": "exped",
        "2": "receb",
        "3": "dest",
    }

    if toma in mapping:
        tomador = _find_text(inf_cte, f"./cte:{mapping[toma]}/cte:xNome")
        if tomador:
            return tomador

    tomador = _find_text(inf_cte, "./cte:ide/cte:toma4/cte:xNome")
    if tomador:
        return tomador

    return (
        _find_text(inf_cte, "./cte:dest/cte:xNome")
        or _find_text(inf_cte, "./cte:rem/cte:xNome")
        or _find_text(inf_cte, "./cte:emit/cte:xNome")
    )


def _extract_weight_ton(inf_cte: ET.Element) -> tuple[Decimal, str]:
    peso_ton = Decimal("0")
    origem_peso = ""
    quantidade_ton = Decimal("0")

    for inf_q in inf_cte.findall(".//cte:infCarga/cte:infQ", NS):
        unidade = _find_text(inf_q, "cte:cUnid")
        tipo_medida = _normalize_text(_find_text(inf_q, "cte:tpMed"))
        quantidade = _parse_decimal(_find_text(inf_q, "cte:qCarga"))

        if quantidade <= 0:
            continue

        if unidade == "02":
            quantidade_convertida = quantidade
        elif unidade == "01":
            quantidade_convertida = quantidade / Decimal("1000")
        else:
            quantidade_convertida = quantidade / Decimal("1000") if quantidade >= Decimal("1000") else quantidade

        if "PESO" in tipo_medida and quantidade_convertida > 0:
            peso_ton = quantidade_convertida
            origem_peso = "peso"
            break

        if quantidade_ton == 0 and ("QUANTIDADE" in tipo_medida or unidade == "03"):
            quantidade_ton = quantidade_convertida

    if peso_ton > 0:
        return _quantize(peso_ton), origem_peso

    if quantidade_ton > 0:
        return _quantize(quantidade_ton), "quantidade"

    return Decimal("0.00"), ""


def parse_cte_xml(xml_bytes: bytes, user) -> dict:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("XML de CT-e inválido.") from exc

    inf_cte = root.find(".//cte:infCte", NS)
    if inf_cte is None:
        raise ValueError("Estrutura de CT-e não encontrada no XML informado.")

    motorista_nome_xml = _extract_driver_name(inf_cte)
    motorista_cpf_xml = _extract_driver_cpf(inf_cte)
    origem = _title_case_city(_find_text(inf_cte, "./cte:ide/cte:xMunIni") or _find_text(inf_cte, "./cte:rem/cte:enderReme/cte:xMun"))
    destino = _title_case_city(_find_text(inf_cte, "./cte:dest/cte:enderDest/cte:xMun") or _find_text(inf_cte, "./cte:ide/cte:xMunFim"))
    cliente = _resolve_tomador_name(inf_cte)
    numero_cte = _find_text(inf_cte, "./cte:ide/cte:nCT")
    data_emissao = _find_text(inf_cte, "./cte:ide/cte:dhEmi")

    data = ""
    if data_emissao:
        data = datetime.fromisoformat(data_emissao).date().isoformat()

    peso_ton, origem_peso = _extract_weight_ton(inf_cte)

    frete_peso = Decimal("0")
    for comp in inf_cte.findall(".//cte:vPrest/cte:Comp", NS):
        nome = _normalize_text(_find_text(comp, "cte:xNome"))
        if "FRETE PESO" in nome:
            frete_peso = _parse_decimal(_find_text(comp, "cte:vComp"))
            break

    if frete_peso <= 0:
        frete_peso = _parse_decimal(_find_text(inf_cte, "./cte:vPrest/cte:vTPrest"))

    valor_tonelada = _quantize(frete_peso / peso_ton) if peso_ton > 0 else Decimal("0.00")

    motorista = None
    if motorista_cpf_xml:
        for candidato in Motorista.objects.filter(usuario=user):
            if _digits_only(candidato.cpf) == motorista_cpf_xml:
                motorista = candidato
                break

    observacoes = []
    if origem_peso == "quantidade":
        observacoes.append("Peso preenchido a partir da quantidade do XML porque o campo de peso veio zerado.")
    if not motorista:
        observacoes.append("Nenhum motorista foi vinculado automaticamente pelo CPF do CT-e. Selecione manualmente antes de salvar.")

    return {
        "motorista": motorista.id if motorista else None,
        "motorista_nome_xml": motorista_nome_xml,
        "origem": origem,
        "destino": destino,
        "cliente": cliente,
        "peso": f"{peso_ton:.2f}",
        "valor_total_informado": f"{_quantize(frete_peso):.2f}",
        "valor_tonelada": f"{valor_tonelada:.2f}",
        "data": data,
        "pago": False,
        "teve_cte": True,
        "numero_cte": numero_cte,
        "observacoes": observacoes,
    }
