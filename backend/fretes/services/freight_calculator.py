from __future__ import annotations

from fretes.services.antt_table_service import ANTTTableService
from fretes.services.geocoding_service import GeocodingService
from fretes.services.routing_service import RoutingService
from fretes.utils.money import round_money, to_decimal


def _build_route_city_samples(route_points: list[dict], geocoding_service: GeocodingService, origem: dict, destino: dict) -> list[str]:
    if len(route_points) < 3:
        return [f"{origem['cidade']} - {origem['estado']}", f"{destino['cidade']} - {destino['estado']}"]

    checkpoints = []
    total_points = len(route_points)
    for factor in (0.25, 0.5, 0.75):
        index = min(total_points - 1, max(1, int(total_points * factor)))
        checkpoints.append(route_points[index])

    cities = [f"{origem['cidade']} - {origem['estado']}"]
    seen = {cities[0].lower(), f"{destino['cidade']} - {destino['estado']}".lower()}
    for point in checkpoints:
        reverse = geocoding_service.reverse_geocode(lat=point["lat"], lng=point["lng"])
        if not reverse.get("cidade"):
            continue
        label = reverse["cidade"]
        if reverse.get("estado"):
            label = f"{label} - {reverse['estado']}"
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        cities.append(label)
    cities.append(f"{destino['cidade']} - {destino['estado']}")
    return cities


def calcular_frete(payload: dict, user=None) -> dict:
    del user
    geocoding_service = GeocodingService()
    routing_service = RoutingService()
    antt_table_service = ANTTTableService()

    origem = geocoding_service.geocode(
        city=payload["cidade_origem"],
        state=payload.get("estado_origem", ""),
        target="origem",
    )
    destino = geocoding_service.geocode(
        city=payload["cidade_destino"],
        state=payload.get("estado_destino", ""),
        target="destino",
    )
    rota = routing_service.calculate_route(origin=origem, destination=destino, payload=payload)

    quantidade_eixos = int(payload["quantidade_eixos"])
    composicao_veicular = bool(payload.get("composicao_veicular", True))
    alto_desempenho = bool(payload.get("alto_desempenho", False))
    retorno_vazio = bool(payload.get("retorno_vazio", False))
    distancia_km = to_decimal(rota["distancia_km"])
    percentual_lucro_adicional = to_decimal(payload.get("percentual_lucro_adicional", 0))
    peso_estimado_toneladas = to_decimal(payload.get("peso_estimado_toneladas", 0))

    coefficients = antt_table_service.resolve_coefficients(
        tipo_carga=payload["tipo_carga"],
        quantidade_eixos=quantidade_eixos,
        composicao_veicular=composicao_veicular,
        alto_desempenho=alto_desempenho,
    )
    valores_antt = antt_table_service.calcular_valores(
        distancia_km=distancia_km,
        coefficients=coefficients,
        retorno_vazio=retorno_vazio,
    )

    avisos = [
        "O valor de pedágio não está incluído no piso mínimo e deve ser acrescido separadamente quando houver.",
        "As despesas extras do transporte e do caminhoneiro previstas na resolução devem ser negociadas à parte.",
    ]
    if coefficients["ajuste_eixos"]:
        avisos.append(coefficients["ajuste_eixos"])

    valor_total = valores_antt["valor_total"]
    frete = {
        "valor_total_sem_lucro_adicional": float(valor_total),
        "valor_total": float(valor_total),
    }
    if payload.get("adicionar_lucro_adicional"):
        valor_total = round_money(valor_total * (1 + (percentual_lucro_adicional / 100)))
        frete.update(
            {
                "percentual_lucro_adicional": float(percentual_lucro_adicional),
                "valor_total_com_lucro_adicional": float(valor_total),
                "valor_total": float(valor_total),
            }
        )

    route_points = rota.get("geometria_preview") or []
    cidades_rota = _build_route_city_samples(route_points=route_points, geocoding_service=geocoding_service, origem=origem, destino=destino)

    return {
        "origem": origem,
        "destino": destino,
        "rota": {
            **rota,
            "cidades_referencia": cidades_rota,
        },
        "antt": {
            "tipo_carga": coefficients["tipo_carga"],
            "tipo_carga_label": coefficients["tipo_carga_label"],
            "tipo_carga_descricao": coefficients["tipo_carga_descricao"],
            "tabela_codigo": coefficients["tabela_codigo"],
            "tabela_label": coefficients["tabela_label"],
            "tabela_descricao": coefficients["tabela_descricao"],
            "quantidade_eixos_informada": coefficients["quantidade_eixos_informada"],
            "quantidade_eixos_aplicada": coefficients["quantidade_eixos_aplicada"],
            "ccd": float(coefficients["ccd"]),
            "cc": float(coefficients["cc"]),
            "retorno_vazio_factor": float(coefficients["retorno_vazio_factor"]),
            "referencia": coefficients["referencia"],
            "referencia_url": coefficients["referencia_url"],
            "eixos_disponiveis": coefficients["eixos_disponiveis"],
        },
        "calculo": {
            "distancia_km": float(round_money(distancia_km)),
            "valor_ida": float(valores_antt["valor_ida"]),
            "valor_retorno_vazio": float(valores_antt["valor_retorno_vazio"]),
            "valor_total_tabela_antt": float(valores_antt["valor_total"]),
        },
        "frete": frete,
        "rentabilidade": {
            "peso_estimado_toneladas": float(round_money(peso_estimado_toneladas)),
            "valor_por_tonelada": (
                float(round_money(valor_total / peso_estimado_toneladas))
                if peso_estimado_toneladas > 0
                else None
            ),
            "sugestoes_valor_por_tonelada": (
                {
                    "lucro_10": float(round_money((valor_total * to_decimal("1.10")) / peso_estimado_toneladas)),
                    "lucro_20": float(round_money((valor_total * to_decimal("1.20")) / peso_estimado_toneladas)),
                    "lucro_30": float(round_money((valor_total * to_decimal("1.30")) / peso_estimado_toneladas)),
                }
                if peso_estimado_toneladas > 0
                else {}
            ),
        },
        "parametros": {
            "quantidade_eixos": quantidade_eixos,
            "tipo_carga": payload.get("tipo_carga"),
            "composicao_veicular": composicao_veicular,
            "alto_desempenho": alto_desempenho,
            "retorno_vazio": retorno_vazio,
            "peso_estimado_toneladas": float(round_money(peso_estimado_toneladas)),
        },
        "avisos": avisos,
    }
