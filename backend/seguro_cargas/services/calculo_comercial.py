from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fretes.utils.money import round_money, to_decimal

from .calculo_seguro import calcular_seguro


def _percent_quantizer(precision: int) -> Decimal:
    return Decimal("1").scaleb(-precision)


def _round_percent(value: Decimal, precision: int) -> Decimal:
    return value.quantize(_percent_quantizer(precision), rounding=ROUND_HALF_UP)


def _as_string(value: Decimal, precision: int | None = None) -> str:
    if precision is None:
        return f"{round_money(value):.2f}"
    return f"{value:.{precision}f}"


def calcular_seguro_comercial(
    *,
    origem: str,
    destino: str,
    valor_carga: object,
    valor_rctr_c: object | None = None,
    valor_rcdc: object | None = None,
    multiplicador: object = "2",
    acrescimo_fixo: object = "6",
    piso_comercial: object = "30",
    proporcao_rctrc: object = "50",
    precisao_percentual: int = 6,
    percentual_rctrc_manual: object | None = None,
    percentual_rcdc_manual: object | None = None,
    taxa_real_rctrc: object | None = None,
    taxa_real_rcdc: object | None = None,
    piso_minimo_antt: object = "0",
    margem_adicional: object = "200",
    pedagio: object = "0",
    outras_despesas: object = "0",
) -> dict:
    carga = round_money(valor_carga)
    if carga <= 0:
        raise ValueError("O valor total da carga deve ser maior que zero.")

    base_rctrc = carga if valor_rctr_c is None else round_money(valor_rctr_c)
    base_rcdc = carga if valor_rcdc is None else round_money(valor_rcdc)
    planilha = calcular_seguro(
        origem=origem,
        destino=destino,
        valor_rctr_c=base_rctrc,
        valor_rcdc=base_rcdc,
    )
    valor_planilha = round_money(planilha["total"])
    multiplicador_decimal = to_decimal(multiplicador)
    acrescimo_decimal = round_money(acrescimo_fixo)
    piso_decimal = round_money(piso_comercial)
    valor_formula = round_money((valor_planilha * multiplicador_decimal) + acrescimo_decimal)
    seguro_final = max(piso_decimal, valor_formula)
    seguro_final = round_money(seguro_final)

    manual = percentual_rctrc_manual is not None and percentual_rcdc_manual is not None
    if manual:
        percentual_rctrc = _round_percent(to_decimal(percentual_rctrc_manual), precisao_percentual)
        percentual_rcdc = _round_percent(to_decimal(percentual_rcdc_manual), precisao_percentual)
        valor_alvo_rctrc = round_money(carga * percentual_rctrc / Decimal("100"))
        valor_alvo_rcdc = round_money(carga * percentual_rcdc / Decimal("100"))
        distribuicao_label = "Percentuais informados manualmente"
    else:
        proporcao = to_decimal(proporcao_rctrc)
        valor_alvo_rctrc = round_money(seguro_final * proporcao / Decimal("100"))
        valor_alvo_rcdc = round_money(seguro_final - valor_alvo_rctrc)
        percentual_rctrc = _round_percent(valor_alvo_rctrc * Decimal("100") / carga, precisao_percentual)
        percentual_rcdc = _round_percent(valor_alvo_rcdc * Decimal("100") / carga, precisao_percentual)
        distribuicao_label = "Distribuição ilustrativa" if proporcao == Decimal("50") else "Distribuição comercial configurada"

    valor_efetivo_rctrc = round_money(carga * percentual_rctrc / Decimal("100"))
    valor_efetivo_rcdc = round_money(carga * percentual_rcdc / Decimal("100"))
    seguro_reconstituido = round_money(valor_efetivo_rctrc + valor_efetivo_rcdc)
    diferenca = round_money(seguro_reconstituido - seguro_final)

    piso_antt = round_money(piso_minimo_antt)
    margem = round_money(margem_adicional)
    pedagio_decimal = round_money(pedagio)
    outras_despesas_decimal = round_money(outras_despesas)
    subtotal_comercial = round_money(piso_antt + seguro_final + margem)
    valor_final = round_money(subtotal_comercial + pedagio_decimal + outras_despesas_decimal)

    return {
        "origem": planilha["origem"],
        "destino": planilha["destino"],
        "valor_carga": _as_string(carga),
        "planilha": {
            **planilha,
            "valor_original": _as_string(valor_planilha),
        },
        "seguro": {
            "valor_formula_antes_piso": _as_string(valor_formula),
            "valor_final": _as_string(seguro_final),
            "piso_aplicado": seguro_final == piso_decimal and valor_formula < piso_decimal,
            "parametros": {
                "multiplicador": str(multiplicador_decimal),
                "acrescimo_fixo": _as_string(acrescimo_decimal),
                "piso_comercial": _as_string(piso_decimal),
            },
        },
        "percentuais": {
            "origem": "manual" if manual else "distribuicao",
            "descricao": distribuicao_label,
            "precisao": precisao_percentual,
            "proporcao_rctrc": str(to_decimal(proporcao_rctrc)),
            "proporcao_rcdc": str(Decimal("100") - to_decimal(proporcao_rctrc)),
            "rctrc": _as_string(percentual_rctrc, precisao_percentual),
            "rcdc": _as_string(percentual_rcdc, precisao_percentual),
            "valor_alvo_rctrc": _as_string(valor_alvo_rctrc),
            "valor_alvo_rcdc": _as_string(valor_alvo_rcdc),
            "valor_efetivo_rctrc": _as_string(valor_efetivo_rctrc),
            "valor_efetivo_rcdc": _as_string(valor_efetivo_rcdc),
            "seguro_reconstituido": _as_string(seguro_reconstituido),
            "seguro_esperado": _as_string(seguro_final),
            "diferenca_arredondamento": _as_string(diferenca),
            "reproduz_exatamente": diferenca == Decimal("0.00"),
            "taxas_reais_referencia": {
                "rctrc": str(to_decimal(taxa_real_rctrc)) if taxa_real_rctrc is not None else None,
                "rcdc": str(to_decimal(taxa_real_rcdc)) if taxa_real_rcdc is not None else None,
                "descricao": "Referência informada pelo usuário; não altera a distribuição comercial.",
            },
        },
        "valor_final": {
            "piso_minimo_antt": _as_string(piso_antt),
            "seguro_final": _as_string(seguro_final),
            "margem_adicional": _as_string(margem),
            "subtotal_sem_pedagio": _as_string(subtotal_comercial),
            "pedagio": _as_string(pedagio_decimal),
            "outras_despesas": _as_string(outras_despesas_decimal),
            "total": _as_string(valor_final),
        },
    }
