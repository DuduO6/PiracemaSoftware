REGIOES_LOGISTICAS = {
    "TRIANGULO_MINEIRO": {
        "nome": "Triângulo Mineiro e Alto Paranaíba",
        "estado": "MG",
        "cidades": (
            "Araguari", "Araxá", "Capinópolis", "Carmo do Paranaíba", "Coromandel",
            "Frutal", "Ibiá", "Indianópolis", "Ituiutaba", "Iturama", "Monte Carmelo",
            "Patos de Minas", "Patrocínio", "Prata", "Rio Paranaíba", "Sacramento",
            "São Gotardo", "Serra do Salitre", "Tupaciguara", "Uberaba", "Uberlândia",
        ),
    },
}


def regioes_serializadas():
    return [
        {"codigo": codigo, **dados, "cidades": list(dados["cidades"])}
        for codigo, dados in REGIOES_LOGISTICAS.items()
    ]
