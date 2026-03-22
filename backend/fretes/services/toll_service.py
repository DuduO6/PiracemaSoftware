from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from urllib.request import Request, urlopen

from fretes.constants import HTTP_TIMEOUT_SECONDS, TOLLS_API_BASE_URL, TOLLS_API_KEY, TOLL_PROVIDER
from fretes.exceptions import ProviderConfigurationError, TollEstimationError
from fretes.utils.money import round_money, to_decimal


class BaseTollProvider(ABC):
    @abstractmethod
    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        raise NotImplementedError


class DisabledTollProvider(BaseTollProvider):
    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        return {
            "quantidade": 0,
            "total": 0.0,
            "itens": [],
            "disponivel": False,
            "estimado": True,
            "mensagem": "Pedágios indisponíveis. Configure ROUTES_API_KEY ou TOLLS_API_KEY para ativar a estimativa.",
            "provedor": "disabled",
        }


class GoogleRoutesTollProvider(BaseTollProvider):
    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        if not TOLLS_API_KEY:
            raise ProviderConfigurationError("TOLLS_API_KEY não configurada para o provedor de pedágios.")

        request_body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin["coordenadas"]["lat"],
                        "longitude": origin["coordenadas"]["lng"],
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination["coordenadas"]["lat"],
                        "longitude": destination["coordenadas"]["lng"],
                    }
                }
            },
            "travelMode": "DRIVE",
            "extraComputations": ["TOLLS"],
            "routeModifiers": {
                "vehicleInfo": {
                    "emissionType": "GASOLINE",
                },
                "tollPasses": [],
            },
        }

        quantidade_eixos = payload.get("quantidade_eixos")
        if quantidade_eixos is not None:
            request_body["routeModifiers"]["vehicleInfo"]["axles"] = int(quantidade_eixos)

        request = Request(
            f"{TOLLS_API_BASE_URL}/directions/v2:computeRoutes",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": TOLLS_API_KEY,
                "X-Goog-FieldMask": "routes.travelAdvisory.tollInfo,routes.localizedValues,routes.legs.travelAdvisory",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise TollEstimationError(f"Falha ao consultar o provedor de pedágios: {exc}") from exc

        route_payload = (data.get("routes") or [{}])[0]
        travel_advisory = route_payload.get("travelAdvisory", {})
        toll_info = travel_advisory.get("tollInfo") or {}

        estimated_prices = toll_info.get("estimatedPrice") or toll_info.get("estimatedPrices") or []
        if isinstance(estimated_prices, dict):
            estimated_prices = [estimated_prices]

        total = Decimal("0")
        for price in estimated_prices:
            units = price.get("units") or "0"
            nanos = Decimal(str(price.get("nanos", 0))) / Decimal("1000000000")
            total += Decimal(str(units)) + nanos

        if total == 0:
            raise TollEstimationError()

        return {
            "quantidade": 0,
            "total": float(round_money(total)),
            "itens": [],
            "disponivel": True,
            "estimado": True,
            "mensagem": "Valor de pedágio estimado pelo Google Routes.",
            "provedor": "google_routes",
        }


def build_toll_provider():
    if TOLL_PROVIDER == "disabled":
        return DisabledTollProvider()
    if TOLL_PROVIDER == "google_routes":
        return GoogleRoutesTollProvider()
    raise ProviderConfigurationError(f'Provedor de pedágios "{TOLL_PROVIDER}" não suportado.')


class TollService:
    def __init__(self, provider=None):
        self.provider = provider or build_toll_provider()

    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        response = self.provider.estimate_tolls(origin=origin, destination=destination, route=route, payload=payload)
        total = round_money(to_decimal(response.get("total", 0)))
        items = response.get("itens") or []
        normalized_items = [
            {
                "nome": item.get("nome", "Pedágio"),
                "rodovia": item.get("rodovia", ""),
                "valor": float(round_money(to_decimal(item.get("valor", 0)))),
                "localizacao": item.get("localizacao", ""),
            }
            for item in items
        ]
        return {
            "quantidade": response.get("quantidade", len(normalized_items)),
            "total": float(total),
            "itens": normalized_items,
            "disponivel": response.get("disponivel", True),
            "estimado": response.get("estimado", False),
            "mensagem": response.get("mensagem", ""),
            "provedor": response.get("provedor", TOLL_PROVIDER),
        }
