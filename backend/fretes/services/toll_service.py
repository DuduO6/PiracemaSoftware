from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from math import cos, hypot, radians
from urllib.request import Request, urlopen

from django.apps import apps
from django.utils import timezone

from fretes.constants import (HTTP_TIMEOUT_SECONDS, TOLLS_API_BASE_URL, TOLLS_API_KEY,
                              TOLL_PROVIDER, TOLL_ROUTE_TOLERANCE_METERS)
from fretes.exceptions import ProviderConfigurationError, TollEstimationError
from fretes.utils.money import round_money, to_decimal


class BaseTollProvider(ABC):
    @abstractmethod
    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        raise NotImplementedError

    def get_tolls(self):
        return []

    def update(self, records):
        raise NotImplementedError


def _distance_point_to_segment_meters(point, start, end):
    reference_lat = radians(point[0])
    scale_x = 111320 * cos(reference_lat)
    scale_y = 110540
    px, py = point[1] * scale_x, point[0] * scale_y
    ax, ay = start[1] * scale_x, start[0] * scale_y
    bx, by = end[1] * scale_x, end[0] * scale_y
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return hypot(px - ax, py - ay)
    ratio = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


class InternalTollProvider(BaseTollProvider):
    def __init__(self, tolerance_meters=TOLL_ROUTE_TOLERANCE_METERS):
        self.tolerance_meters = tolerance_meters

    def get_tolls(self):
        PracaPedagio = apps.get_model("inteligencia_logistica", "PracaPedagio")
        return PracaPedagio.objects.filter(ativo=True, latitude__isnull=False, longitude__isnull=False)

    def estimate_tolls(self, origin: dict, destination: dict, route: dict, payload: dict) -> dict:
        geometry = route.get("geometria_preview") or []
        if len(geometry) < 2:
            return {"quantidade": 0, "total": 0, "itens": [], "disponivel": False, "estimado": False,
                    "mensagem": "A rota não retornou geometria suficiente para localizar pedágios.", "provedor": "internal"}
        eixos = int(payload.get("quantidade_eixos") or 2)
        TarifaPedagio = apps.get_model("inteligencia_logistica", "TarifaPedagio")
        hoje = timezone.localdate()
        itens = []
        for praca in self.get_tolls().prefetch_related("tarifas"):
            point = (float(praca.latitude), float(praca.longitude))
            distancia = min(_distance_point_to_segment_meters(
                point, (float(a["lat"]), float(a["lng"])), (float(b["lat"]), float(b["lng"]))
            ) for a, b in zip(geometry, geometry[1:]))
            if distancia > self.tolerance_meters:
                continue
            tarifa = TarifaPedagio.objects.filter(
                pedagio=praca, quantidade_eixos=eixos, vigencia__lte=hoje
            ).order_by("-vigencia").first()
            if tarifa is None:
                continue
            itens.append({"nome": praca.praca, "rodovia": praca.rodovia, "valor": float(tarifa.valor),
                          "localizacao": f"{praca.cidade}/{praca.estado}", "lat": float(praca.latitude),
                          "lng": float(praca.longitude), "fonte": tarifa.fonte, "distancia_rota_m": round(distancia, 1)})
        total = sum((Decimal(str(item["valor"])) for item in itens), Decimal("0"))
        existem_pracas = self.get_tolls().exists()
        return {"quantidade": len(itens), "total": float(round_money(total)), "itens": itens,
                "disponivel": existem_pracas, "estimado": False,
                "mensagem": "Tarifas calculadas pela base interna." if existem_pracas else "A base interna de pedágios ainda não possui praças georreferenciadas.",
                "provedor": "internal"}


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
    if TOLL_PROVIDER == "internal":
        return InternalTollProvider()
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
                "lat": item.get("lat"),
                "lng": item.get("lng"),
                "fonte": item.get("fonte", ""),
                "distancia_rota_m": item.get("distancia_rota_m"),
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
