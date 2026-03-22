from __future__ import annotations

from decimal import Decimal

from fretes.exceptions import FretesValidationError
from fretes.utils.money import round_money, round_rate, to_decimal


ANTT_REFERENCE_URL = (
    "https://anttlegis.antt.gov.br/action/TematicaAction.php?acao=abrirVinculos&cod_menu=7221&cod_modulo=392"
    "&cotematica=16181785"
)
ANTT_TABLE_REFERENCE = (
    "Resolução ANTT nº 5.867/2020 com redação da Resolução ANTT nº 6.076/2026 "
    "e valores atualizados pela Portaria SUROC nº 04/2026"
)

TABLE_DEFINITIONS = {
    "a": {
        "codigo": "A",
        "label": "Tabela A",
        "descricao": "Transporte rodoviário de carga lotação com contratação da composição veicular ou caminhão simples.",
    },
    "b": {
        "codigo": "B",
        "label": "Tabela B",
        "descricao": "Operações em que haja a contratação apenas do veículo automotor de cargas.",
    },
    "c": {
        "codigo": "C",
        "label": "Tabela C",
        "descricao": "Transporte rodoviário de carga lotação de alto desempenho com contratação da composição veicular ou caminhão simples.",
    },
    "d": {
        "codigo": "D",
        "label": "Tabela D",
        "descricao": "Operações de alto desempenho em que haja a contratação apenas do veículo automotor de cargas.",
    },
}

CARGO_DEFINITIONS = {
    "granel_solido": {"label": "Granel sólido", "descricao": "Carga sólida a granel, sem embalagem individual."},
    "granel_liquido": {"label": "Granel líquido", "descricao": "Carga líquida transportada a granel."},
    "frigorificada_aquecida": {
        "label": "Frigorificada ou Aquecida",
        "descricao": "Carga que exige controle térmico por refrigeração ou aquecimento.",
    },
    "conteinerizada": {"label": "Conteinerizada", "descricao": "Carga transportada em contêiner."},
    "carga_geral": {"label": "Carga Geral", "descricao": "Carga geral solta, paletizada ou embalada."},
    "neogranel": {"label": "Neogranel", "descricao": "Carga em lotação, normalmente unitizada, sem embalagem final ao consumidor."},
    "perigosa_granel_solido": {
        "label": "Perigosa (granel sólido)",
        "descricao": "Produto perigoso transportado a granel em estado sólido.",
    },
    "perigosa_granel_liquido": {
        "label": "Perigosa (granel líquido)",
        "descricao": "Produto perigoso transportado a granel em estado líquido.",
    },
    "perigosa_frigorificada_aquecida": {
        "label": "Perigosa (frigorificada ou aquecida)",
        "descricao": "Produto perigoso com exigência de controle térmico.",
    },
    "perigosa_conteinerizada": {
        "label": "Perigosa (conteinerizada)",
        "descricao": "Produto perigoso transportado em contêiner.",
    },
    "perigosa_carga_geral": {
        "label": "Perigosa (carga geral)",
        "descricao": "Produto perigoso tratado como carga geral.",
    },
    "granel_pressurizada": {
        "label": "Carga Granel Pressurizada",
        "descricao": "Carga a granel transportada sob pressão.",
    },
}

ANTT_COEFFICIENTS = {
    "a": {
        "granel_solido": {2: ("4.0338", "444.84"), 3: ("5.1660", "533.36"), 4: ("5.8464", "576.59"), 5: ("6.7381", "642.10"), 6: ("7.4408", "656.76"), 7: ("8.0855", "792.30"), 9: ("9.2662", "877.83")},
        "granel_liquido": {2: ("4.1052", "455.84"), 3: ("5.2583", "550.10"), 4: ("5.9955", "600.27"), 5: ("6.9002", "669.38"), 6: ("7.6080", "685.45"), 7: ("8.2192", "811.76"), 9: ("9.4199", "902.80")},
        "frigorificada_aquecida": {2: ("4.7442", "502.29"), 3: ("6.0679", "601.96"), 4: ("6.9216", "663.16"), 5: ("7.9337", "732.07"), 6: ("8.7563", "745.94"), 7: ("9.6471", "949.16"), 9: ("10.9629", "1030.58")},
        "conteinerizada": {3: ("5.1397", "526.13"), 4: ("5.7767", "557.42"), 5: ("6.6765", "625.16"), 6: ("7.3776", "639.38"), 7: ("8.0832", "791.67"), 9: ("9.1859", "855.76")},
        "carga_geral": {2: ("4.0031", "436.39"), 3: ("5.1295", "523.33"), 4: ("5.8178", "568.72"), 5: ("6.7126", "635.08"), 6: ("7.4124", "648.95"), 7: ("8.1252", "803.22"), 9: ("9.2466", "872.44")},
        "neogranel": {2: ("3.6028", "436.39"), 3: ("5.1281", "522.93"), 4: ("5.8441", "575.96"), 5: ("6.7126", "635.08"), 6: ("7.4124", "648.95"), 7: ("8.1252", "803.22"), 9: ("9.2466", "872.44")},
        "perigosa_granel_solido": {2: ("4.7775", "587.98"), 3: ("5.9193", "679.12"), 4: ("6.6352", "727.28"), 5: ("7.5269", "792.80"), 6: ("8.2296", "807.45"), 7: ("8.8919", "947.84"), 9: ("10.0803", "1035.49")},
        "perigosa_granel_liquido": {2: ("4.8611", "610.96"), 3: ("6.0237", "707.85"), 4: ("6.7649", "762.95"), 5: ("7.6697", "832.06"), 6: ("8.3775", "848.13"), 7: ("9.0063", "979.29"), 9: ("10.2147", "1072.44")},
        "perigosa_frigorificada_aquecida": {2: ("5.3315", "609.31"), 3: ("6.6676", "712.41"), 4: ("7.5371", "780.02"), 5: ("8.5492", "848.93"), 6: ("9.3718", "862.80"), 7: ("10.2855", "1072.32"), 9: ("11.6113", "1156.49")},
        "perigosa_conteinerizada": {3: ("5.5109", "623.38"), 4: ("6.1835", "659.60"), 5: ("7.0832", "727.35"), 6: ("7.7843", "741.56"), 7: ("8.5076", "898.70"), 9: ("9.6180", "964.90")},
        "perigosa_carga_geral": {2: ("4.3647", "531.01"), 3: ("5.5008", "620.58"), 4: ("6.2246", "670.91"), 5: ("7.1193", "737.27"), 6: ("7.8191", "751.14"), 7: ("8.5496", "910.26"), 9: ("9.6787", "981.58")},
        "granel_pressurizada": {5: ("7.0646", "731.90"), 6: ("7.8089", "757.99"), 9: ("9.7697", "1016.29")},
    },
    "b": {
        "granel_solido": {4: ("5.2729", "515.17"), 5: ("5.9994", "574.29"), 6: ("6.6896", "588.17"), 7: ("7.1066", "695.68"), 9: ("7.9200", "746.78")},
        "granel_liquido": {4: ("5.3358", "515.17"), 5: ("6.0623", "574.29"), 6: ("6.7525", "588.17"), 7: ("7.1695", "695.68"), 9: ("7.9829", "746.78")},
        "frigorificada_aquecida": {4: ("6.2111", "564.07"), 5: ("7.0457", "623.20"), 6: ("7.8586", "637.07"), 7: ("8.2933", "749.43"), 9: ("9.2644", "802.65")},
        "conteinerizada": {4: ("5.2729", "515.17"), 5: ("5.9994", "574.29"), 6: ("6.6896", "588.17"), 7: ("7.1066", "695.68"), 9: ("7.9200", "746.78")},
        "carga_geral": {4: ("5.2729", "515.17"), 5: ("5.9994", "574.29"), 6: ("6.6896", "588.17"), 7: ("7.1066", "695.68"), 9: ("7.9200", "746.78")},
        "neogranel": {4: ("5.2729", "515.17"), 5: ("5.9994", "574.29"), 6: ("6.6896", "588.17"), 7: ("7.1066", "695.68"), 9: ("7.9200", "746.78")},
        "perigosa_granel_solido": {4: ("6.0617", "665.87"), 5: ("6.7882", "724.99"), 6: ("7.4784", "738.86"), 7: ("7.9130", "851.22"), 9: ("8.7341", "904.44")},
        "perigosa_granel_liquido": {4: ("6.1053", "677.85"), 5: ("6.8318", "736.97"), 6: ("7.5220", "750.84"), 7: ("7.9566", "863.20"), 9: ("8.7777", "916.42")},
        "perigosa_frigorificada_aquecida": {4: ("6.8267", "680.93"), 5: ("7.6612", "740.05"), 6: ("8.4742", "753.93"), 7: ("8.9317", "872.59"), 9: ("9.9128", "928.56")},
        "perigosa_conteinerizada": {4: ("5.6796", "617.35"), 5: ("6.4062", "676.48"), 6: ("7.0963", "690.35"), 7: ("7.5310", "802.71"), 9: ("8.3521", "855.93")},
        "perigosa_carga_geral": {4: ("5.6796", "617.35"), 5: ("6.4062", "676.48"), 6: ("7.0963", "690.35"), 7: ("7.5310", "802.71"), 9: ("8.3521", "855.93")},
        "granel_pressurizada": {5: ("5.9994", "574.29"), 6: ("6.6896", "588.17"), 9: ("7.9200", "746.78")},
    },
    "c": {
        "granel_solido": {2: ("3.4369", "168.42"), 3: ("4.3858", "191.28"), 4: ("5.0084", "207.68"), 5: ("5.7474", "221.79"), 6: ("6.4159", "224.95"), 7: ("6.7870", "261.12"), 9: ("7.7868", "282.59")},
        "granel_liquido": {2: ("3.4827", "170.79"), 3: ("4.4391", "194.88"), 4: ("5.1022", "212.78"), 5: ("5.8459", "227.67"), 6: ("6.5163", "231.13"), 7: ("6.8753", "265.31"), 9: ("7.8823", "287.97")},
        "frigorificada_aquecida": {2: ("4.1215", "198.62"), 3: ("5.2426", "225.01"), 4: ("6.0096", "247.41"), 5: ("6.8611", "262.25"), 6: ("7.6513", "265.24"), 7: ("8.1234", "318.08"), 9: ("9.2734", "339.58")},
        "conteinerizada": {3: ("4.3763", "189.72"), 4: ("4.9834", "203.55"), 5: ("5.7253", "218.14"), 6: ("6.3932", "221.21"), 7: ("6.7861", "260.98"), 9: ("7.7579", "277.83")},
        "carga_geral": {2: ("3.4259", "166.60"), 3: ("4.3727", "189.11"), 4: ("4.9981", "205.98"), 5: ("5.7382", "220.28"), 6: ("6.4057", "223.27"), 7: ("6.8012", "263.47"), 9: ("7.7797", "281.43")},
        "neogranel": {2: ("3.0257", "166.60"), 3: ("4.3722", "189.03"), 4: ("5.0076", "207.54"), 5: ("5.7382", "220.28"), 6: ("6.4057", "223.27"), 7: ("6.8012", "263.47"), 9: ("7.7797", "281.43")},
        "perigosa_granel_solido": {2: ("3.9550", "217.08"), 3: ("4.9142", "241.63"), 4: ("5.5737", "261.22"), 5: ("6.3127", "275.34"), 6: ("6.9812", "278.50"), 7: ("7.3713", "317.80"), 9: ("8.3794", "340.64")},
        "perigosa_granel_liquido": {2: ("3.9850", "222.03"), 3: ("4.9517", "247.82"), 4: ("5.6203", "268.91"), 5: ("6.3640", "283.80"), 6: ("7.0343", "287.26"), 7: ("7.4123", "324.57"), 9: ("8.4276", "348.60")},
        "perigosa_frigorificada_aquecida": {2: ("4.5997", "244.84"), 3: ("5.7343", "273.44"), 4: ("6.5188", "299.98"), 5: ("7.3703", "314.83"), 6: ("8.1605", "317.82"), 7: ("8.6573", "374.73"), 9: ("9.8181", "398.01")},
        "perigosa_conteinerizada": {3: ("4.6358", "229.62"), 4: ("5.2797", "246.64"), 5: ("6.0216", "261.24"), 6: ("6.6895", "264.30"), 7: ("7.1014", "307.21"), 9: ("8.0815", "325.43")},
        "perigosa_carga_geral": {2: ("3.6750", "204.81"), 3: ("4.6321", "229.02"), 4: ("5.2945", "249.08"), 5: ("6.0346", "263.37"), 6: ("6.7020", "266.36"), 7: ("7.1165", "309.70"), 9: ("8.1033", "329.02")},
        "granel_pressurizada": {5: ("5.8647", "241.14"), 6: ("6.5481", "246.76"), 9: ("7.9676", "312.42")},
    },
    "d": {
        "granel_solido": {4: ("4.5780", "194.44"), 5: ("5.1667", "207.18"), 6: ("5.8246", "210.17"), 7: ("6.0332", "240.30"), 9: ("6.7460", "254.35")},
        "granel_liquido": {4: ("4.6409", "194.44"), 5: ("5.2296", "207.18"), 6: ("5.8875", "210.17"), 7: ("6.0961", "240.30"), 9: ("6.8089", "254.35")},
        "frigorificada_aquecida": {4: ("5.5300", "226.06"), 5: ("6.2268", "238.80"), 6: ("7.0074", "241.78"), 7: ("7.2350", "275.04"), 9: ("8.1060", "290.47")},
        "conteinerizada": {4: ("4.5780", "194.44"), 5: ("5.1667", "207.18"), 6: ("5.8246", "210.17"), 7: ("6.0332", "240.30"), 9: ("6.7460", "254.35")},
        "carga_geral": {4: ("4.5780", "194.44"), 5: ("5.1667", "207.18"), 6: ("5.8246", "210.17"), 7: ("6.0332", "240.30"), 9: ("6.7460", "254.35")},
        "neogranel": {4: ("4.5780", "194.44"), 5: ("5.1667", "207.18"), 6: ("5.8246", "210.17"), 7: ("6.0332", "240.30"), 9: ("6.7460", "254.35")},
        "perigosa_granel_solido": {4: ("5.1433", "247.99"), 5: ("5.7321", "260.73"), 6: ("6.3899", "263.72"), 7: ("6.6176", "296.98"), 9: ("7.3386", "312.40")},
        "perigosa_granel_liquido": {4: ("5.1590", "250.57"), 5: ("5.7477", "263.31"), 6: ("6.4056", "266.30"), 7: ("6.6332", "299.56"), 9: ("7.3542", "314.98")},
        "perigosa_frigorificada_aquecida": {4: ("6.0392", "278.63"), 5: ("6.7360", "291.37"), 6: ("7.5166", "294.36"), 7: ("7.7689", "331.70"), 9: ("8.6508", "348.90")},
        "perigosa_conteinerizada": {4: ("4.8743", "237.54"), 5: ("5.4631", "250.28"), 6: ("6.1209", "253.27"), 7: ("6.3486", "286.53"), 9: ("7.0696", "301.95")},
        "perigosa_carga_geral": {4: ("4.8743", "237.54"), 5: ("5.4631", "250.28"), 6: ("6.1209", "253.27"), 7: ("6.3486", "286.53"), 9: ("7.0696", "301.95")},
        "granel_pressurizada": {5: ("5.1667", "207.18"), 6: ("5.8246", "210.17"), 9: ("6.7460", "254.35")},
    },
}


class ANTTTableService:
    retorno_vazio_factor = Decimal("0.92")

    def resolve_operation_table(self, composicao_veicular: bool, alto_desempenho: bool) -> dict:
        if composicao_veicular and alto_desempenho:
            table_key = "c"
        elif composicao_veicular:
            table_key = "a"
        elif alto_desempenho:
            table_key = "d"
        else:
            table_key = "b"
        definition = TABLE_DEFINITIONS[table_key]
        return {"table_key": table_key, **definition}

    def resolve_coefficients(self, tipo_carga: str, quantidade_eixos: int, composicao_veicular: bool, alto_desempenho: bool) -> dict:
        operation = self.resolve_operation_table(
            composicao_veicular=composicao_veicular,
            alto_desempenho=alto_desempenho,
        )
        cargo = CARGO_DEFINITIONS[tipo_carga]
        coefficient_table = ANTT_COEFFICIENTS[operation["table_key"]][tipo_carga]
        supported_axles = sorted(coefficient_table.keys())
        applied_axles = self._resolve_axles(quantidade_eixos, supported_axles)
        ccd_raw, cc_raw = coefficient_table[applied_axles]
        axle_adjustment = None
        if applied_axles != quantidade_eixos:
            axle_adjustment = (
                f"A quantidade de eixos informada ({quantidade_eixos}) não existe nessa tabela para o tipo de carga "
                f"selecionado. Foi aplicado o valor de {applied_axles} eixos conforme a regra de aproximação da ANTT."
            )

        return {
            "tipo_carga": tipo_carga,
            "tipo_carga_label": cargo["label"],
            "tipo_carga_descricao": cargo["descricao"],
            "tabela_codigo": operation["codigo"],
            "tabela_label": operation["label"],
            "tabela_descricao": operation["descricao"],
            "quantidade_eixos_informada": quantidade_eixos,
            "quantidade_eixos_aplicada": applied_axles,
            "ccd": round_rate(Decimal(ccd_raw)),
            "cc": round_money(Decimal(cc_raw)),
            "retorno_vazio_factor": self.retorno_vazio_factor,
            "referencia": ANTT_TABLE_REFERENCE,
            "referencia_url": ANTT_REFERENCE_URL,
            "ajuste_eixos": axle_adjustment,
            "eixos_disponiveis": supported_axles,
        }

    def calcular_valores(self, distancia_km: Decimal, coefficients: dict, retorno_vazio: bool) -> dict:
        ccd = to_decimal(coefficients["ccd"])
        cc = to_decimal(coefficients["cc"])
        valor_ida = round_money((distancia_km * ccd) + cc)
        valor_retorno_vazio = round_money(self.retorno_vazio_factor * distancia_km * ccd) if retorno_vazio else Decimal("0.00")
        valor_total = round_money(valor_ida + valor_retorno_vazio)
        return {
            "distancia_km": round_money(distancia_km),
            "valor_ida": valor_ida,
            "valor_retorno_vazio": valor_retorno_vazio,
            "valor_total": valor_total,
        }

    @staticmethod
    def _resolve_axles(requested_axles: int, supported_axles: list[int]) -> int:
        if requested_axles in supported_axles:
            return requested_axles

        lower = [axle for axle in supported_axles if axle < requested_axles]
        if lower:
            return max(lower)

        higher = [axle for axle in supported_axles if axle > requested_axles]
        if higher:
            return min(higher)

        raise FretesValidationError("Não foi possível localizar uma quantidade de eixos compatível na tabela ANTT.")
