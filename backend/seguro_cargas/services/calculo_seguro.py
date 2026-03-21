from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .tabela_deslocamentos import (
    buscar_taxa_deslocamento,
    localidade_tem_taxa_fluvial,
    obter_label_localidade,
)


CASAS_DECIMAIS = Decimal("0.01")
CASAS_TAXA_BASE = Decimal("0.0001")


def _decimal(valor: object) -> Decimal:
    return Decimal(str(valor))


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)


def _arredondar_taxa(valor: Decimal) -> Decimal:
    return valor.quantize(CASAS_TAXA_BASE, rounding=ROUND_HALF_UP)


# Constantes configuráveis extraídas da planilha original.
# Pontos que exigem validação com a regra de negócio:
# - TAXA_RJ: a célula J3 aparenta estar vazia no arquivo recebido.
# - TAXA_UNICA_RCT, TAXA_AMBIENTAL, TAXA_FLUVIAL, TAXA_DDR,
#   TAXA_EMBARCADOR, TAXA_DIFERENCIADA_VALOR_IS, TAXA_MP_NOVO, TAXA_MP_USADO:
#   não vieram preenchidas e por isso ficam com default 0.0.
DESCONTO_TABELA = _decimal("0.5")
ADICIONAL_AVARIAS = _decimal("0.01")
TAXA_UNICA_DC = _decimal("0.02")
TAXA_RJ = _decimal("0.0")
TAXA_UNICA_RCT = _decimal("0.0")
TAXA_AMBIENTAL = _decimal("0.0")
TAXA_FLUVIAL = _decimal("0.0")
TAXA_DDR = _decimal("0.0")
TAXA_EMBARCADOR = _decimal("0.0")
TAXA_DIFERENCIADA_VALOR_IS = _decimal("0.0")
TAXA_MP_NOVO = _decimal("0.0")
TAXA_MP_USADO = _decimal("0.0")
IOF = _decimal("0.0738")

# Ambiguidade da planilha:
# o prompt original menciona J5 tanto como "taxa_embarcador" quanto como
# possível sobrescrita manual do valor do RCTR-C. Deixamos a sobrescrita
# isolada nesta constante para facilitar a validação com a área de negócio.
VALOR_MANUAL_RCTR_C = None


def calcular_seguro(origem: str, destino: str, valor_rctr_c: object, valor_rcdc: object) -> dict:
    valor_rctr_c_decimal = _decimal(valor_rctr_c)
    valor_rcdc_decimal = _decimal(valor_rcdc)

    taxa_base_float, modo_busca, origem_canonica, destino_canonico = buscar_taxa_deslocamento(
        origem=origem,
        destino=destino,
    )
    taxa_base = _decimal(taxa_base_float)

    taxa_fluvial_aplicada = TAXA_FLUVIAL if localidade_tem_taxa_fluvial(origem_canonica, destino_canonico) else _decimal("0.0")

    if VALOR_MANUAL_RCTR_C is not None:
        rctr_c_sem_iof = _arredondar(_decimal(VALOR_MANUAL_RCTR_C))
    else:
        taxa_com_desconto = taxa_base - (DESCONTO_TABELA * taxa_base)
        taxa_final = (
            taxa_com_desconto
            + TAXA_UNICA_RCT
            + TAXA_AMBIENTAL
            + ADICIONAL_AVARIAS
            + TAXA_DDR
            + TAXA_EMBARCADOR
            + TAXA_DIFERENCIADA_VALOR_IS
            + TAXA_MP_NOVO
            + TAXA_MP_USADO
            + taxa_fluvial_aplicada
        )
        rctr_c_sem_iof = _arredondar((taxa_final * valor_rctr_c_decimal) / _decimal("100"))

    rctr_c_com_iof = _arredondar(rctr_c_sem_iof * (_decimal("1") + IOF))

    rcdc_sem_iof = _arredondar(((TAXA_UNICA_DC + TAXA_RJ) * valor_rcdc_decimal) / _decimal("100"))
    rcdc_com_iof = _arredondar(rcdc_sem_iof * (_decimal("1") + IOF))
    total = _arredondar(rctr_c_com_iof + rcdc_com_iof)

    return {
        "origem": obter_label_localidade(origem_canonica),
        "destino": obter_label_localidade(destino_canonico),
        "taxa_base_encontrada": float(_arredondar_taxa(taxa_base)),
        "taxa_base_modo_busca": modo_busca,
        "rctr_c_sem_iof": float(rctr_c_sem_iof),
        "rctr_c_com_iof": float(rctr_c_com_iof),
        "rcdc_sem_iof": float(rcdc_sem_iof),
        "rcdc_com_iof": float(rcdc_com_iof),
        "total": float(total),
        "taxas_aplicadas": {
            "desconto_tabela": float(DESCONTO_TABELA),
            "taxa_unica_rct": float(TAXA_UNICA_RCT),
            "taxa_ambiental": float(TAXA_AMBIENTAL),
            "taxa_fluvial": float(taxa_fluvial_aplicada),
            "taxa_ddr": float(TAXA_DDR),
            "adicional_avarias": float(ADICIONAL_AVARIAS),
            "taxa_embarcador": float(TAXA_EMBARCADOR),
            "taxa_diferenciada_valor_is": float(TAXA_DIFERENCIADA_VALOR_IS),
            "taxa_mp_novo": float(TAXA_MP_NOVO),
            "taxa_mp_usado": float(TAXA_MP_USADO),
            "taxa_unica_dc": float(TAXA_UNICA_DC),
            "taxa_rj": float(TAXA_RJ),
            "iof": float(IOF),
            "valor_manual_rctr_c": float(_decimal(VALOR_MANUAL_RCTR_C)) if VALOR_MANUAL_RCTR_C is not None else None,
        },
    }
