import json
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .exceptions import MdfeConfigurationError, MdfeError


UF_CODES = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53", "EX": "99",
}
UF_BY_CODE = {value: key for key, value in UF_CODES.items()}


def normalize_cnpj(value):
    value = re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", value):
        raise MdfeError("Informe um CNPJ válido com 14 posições.", code="invalid_cnpj")
    if value.isdigit() and not _valid_numeric_cnpj(value):
        raise MdfeError("O CNPJ informado possui dígitos verificadores inválidos.", code="invalid_cnpj")
    return value


def _valid_numeric_cnpj(value):
    if len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for size, weights in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
                          (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        remainder = sum(digit * weight for digit, weight in zip(digits[:size], weights)) % 11
        expected = 0 if remainder < 2 else 11 - remainder
        if digits[size] != expected:
            return False
    return True


def validate_access_key(value):
    value = str(value or "").strip().upper()
    if not re.fullmatch(r"[0-9]{6}[A-Z0-9]{12}[0-9]{26}", value):
        raise MdfeError("Chave de acesso do MDF-e inválida.", code="invalid_access_key")
    if value[20:22] != "58":
        raise MdfeError("A chave informada não pertence a um MDF-e modelo 58.", code="invalid_access_key")
    if value.isdigit():
        total = sum(int(digit) * weight for digit, weight in zip(reversed(value[:-1]), [2, 3, 4, 5, 6, 7, 8, 9] * 6))
        remainder = total % 11
        expected = 0 if remainder in (0, 1) else 11 - remainder
        if int(value[-1]) != expected:
            raise MdfeError("Dígito verificador da chave do MDF-e inválido.", code="invalid_access_key")
    return value


def access_key_data(key):
    key = validate_access_key(key)
    return {
        "uf_code": key[:2],
        "year_month": key[2:6],
        "issuer_cnpj": key[6:20],
        "number": key[25:34],
    }


def normalize_uf(value):
    value = str(value or "").strip().upper()
    if value not in UF_CODES:
        raise MdfeError("UF inválida.", code="invalid_uf")
    return value


@lru_cache(maxsize=1)
def _municipalities():
    source = Path(settings.MDFE_MUNICIPALITIES_FILE)
    if not source.is_file():
        raise MdfeConfigurationError(
            "A base local de municípios do IBGE não está disponível.", code="municipalities_not_configured"
        )
    with source.open("r", encoding="utf-8") as file:
        values = json.load(file)
    return {str(item["id"]): item for item in values}


def validate_municipality(code, uf):
    code = str(code or "").strip()
    uf = normalize_uf(uf)
    if uf == "EX":
        if code != "9999999":
            raise MdfeError("Para encerramento no exterior, use o município 9999999.", code="invalid_municipality")
        return {"id": code, "cidade": "Exterior", "estado": "EX", "label": "Exterior"}
    if not re.fullmatch(r"[0-9]{7}", code):
        raise MdfeError("Código IBGE do município inválido.", code="invalid_municipality")
    item = _municipalities().get(code)
    if not item:
        raise MdfeError("Município não encontrado na base IBGE local.", code="invalid_municipality")
    if item["estado"] != uf or code[:2] != UF_CODES[uf]:
        raise MdfeError("O município informado não pertence à UF selecionada.", code="municipality_uf_mismatch")
    return item
