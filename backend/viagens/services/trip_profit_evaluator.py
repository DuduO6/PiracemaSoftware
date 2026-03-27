from __future__ import annotations

from decimal import Decimal

from fretes.services.geocoding_service import GeocodingService
from fretes.services.routing_service import RoutingService
from fretes.utils.money import round_money, to_decimal

from viagens.models import Viagem


COMISSAO_PERCENTUAL = Decimal("0.13")


def avaliar_lucro_viagem(*, viagem: Viagem, payload: dict) -> dict:
    geocoding_service = GeocodingService()
    routing_service = RoutingService()

    origem_nome = payload.get("cidade_origem") or viagem.origem
    estado_origem = payload.get("estado_origem", "")
    destino_nome = payload.get("cidade_destino") or viagem.destino
    estado_destino = payload.get("estado_destino", "")

    origem = geocoding_service.geocode(city=origem_nome, state=estado_origem, target="origem")
    destino = geocoding_service.geocode(city=destino_nome, state=estado_destino, target="destino")
    rota = routing_service.calculate_route(origin=origem, destination=destino, payload=payload)

    media_km_por_litro = to_decimal(payload["media_km_por_litro"])
    preco_combustivel = to_decimal(payload["preco_combustivel"])
    distancia_km = to_decimal(rota["distancia_km"])
    litros_estimados = round_money(distancia_km / media_km_por_litro)
    custo_combustivel = round_money(litros_estimados * preco_combustivel)

    faturamento = to_decimal(viagem.valor_total)
    comissao_motorista = round_money(faturamento * COMISSAO_PERCENTUAL)
    lucro_liquido = round_money(faturamento - comissao_motorista - custo_combustivel)
    margem_percentual = round_money((lucro_liquido / faturamento) * 100) if faturamento > 0 else Decimal("0")

    return {
        "viagem": {
            "id": viagem.id,
            "data": viagem.data,
            "cliente": viagem.cliente,
            "motorista_id": viagem.motorista_id,
            "motorista_nome": viagem.motorista.nome,
            "origem_lancada": viagem.origem,
            "destino_lancado": viagem.destino,
            "peso": float(round_money(viagem.peso)),
            "valor_tonelada": float(round_money(viagem.valor_tonelada)),
            "faturamento_total": float(round_money(viagem.valor_total)),
        },
        "origem": origem,
        "destino": destino,
        "rota": {
            **rota,
        },
        "custos": {
            "media_km_por_litro": float(round_money(media_km_por_litro)),
            "preco_combustivel": float(round_money(preco_combustivel)),
            "litros_estimados": float(litros_estimados),
            "custo_combustivel": float(custo_combustivel),
        },
        "motorista": {
            "comissao_percentual": float(round_money(COMISSAO_PERCENTUAL * 100)),
            "comissao_valor": float(comissao_motorista),
        },
        "resultado": {
            "lucro_liquido": float(lucro_liquido),
            "margem_percentual": float(margem_percentual),
        },
    }
