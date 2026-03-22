from __future__ import annotations

import json
from abc import ABC, abstractmethod
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fretes.constants import (
    HTTP_TIMEOUT_SECONDS,
    HTTP_USER_AGENT,
    OSRM_BASE_URL,
    ROUTES_API_BASE_URL,
    ROUTES_API_KEY,
    ROUTING_PROVIDER,
)
from fretes.exceptions import ProviderConfigurationError, RouteCalculationError


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}min"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"


def simplify_route_coordinates(coordinates: list[list[float]], max_points: int = 80) -> list[dict]:
    if not coordinates:
        return []
    if len(coordinates) <= max_points:
        return [{"lat": lat, "lng": lng} for lng, lat in coordinates]

    step = max(1, len(coordinates) // max_points)
    sampled = coordinates[::step]
    if sampled[-1] != coordinates[-1]:
        sampled.append(coordinates[-1])
    return [{"lat": lat, "lng": lng} for lng, lat in sampled]


def decode_google_polyline(encoded: str) -> list[list[float]]:
    index = 0
    lat = 0
    lng = 0
    coordinates = []

    while index < len(encoded):
        result = 1
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lat += ~(result >> 1) if result & 1 else result >> 1

        result = 1
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lng += ~(result >> 1) if result & 1 else result >> 1

        coordinates.append([lng / 1e5, lat / 1e5])

    return coordinates


class BaseRoutingProvider(ABC):
    @abstractmethod
    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        raise NotImplementedError


class OsrmRoutingProvider(BaseRoutingProvider):
    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        coordinates = (
            f"{origin['coordenadas']['lng']},{origin['coordenadas']['lat']};"
            f"{destination['coordenadas']['lng']},{destination['coordenadas']['lat']}"
        )
        params = urlencode({"overview": "full", "steps": "true", "alternatives": "false", "geometries": "geojson"})
        request = Request(
            f"{OSRM_BASE_URL}/route/v1/driving/{coordinates}?{params}",
            headers={"User-Agent": HTTP_USER_AGENT},
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RouteCalculationError(f"Falha ao consultar o provedor de rotas: {exc}") from exc

        routes = data.get("routes") or []
        if not routes:
            raise RouteCalculationError()

        route = routes[0]
        distance_meters = int(round(route.get("distance", 0)))
        duration_seconds = int(round(route.get("duration", 0)))
        route_geometry = (route.get("geometry") or {}).get("coordinates") or []
        legs = route.get("legs") or []
        road_names = []
        if legs:
            for step in legs[0].get("steps") or []:
                name = (step.get("name") or "").strip()
                if name and name not in road_names:
                    road_names.append(name)
                if len(road_names) >= 8:
                    break

        return {
            "distancia_metros": distance_meters,
            "distancia_km": round(distance_meters / 1000, 2),
            "duracao_segundos": duration_seconds,
            "duracao_formatada": format_duration(duration_seconds),
            "geometria_preview": simplify_route_coordinates(route_geometry),
            "rodovias_referencia": road_names,
            "provedor": "osrm",
            "dados_brutos": route,
        }


class GoogleRoutesProvider(BaseRoutingProvider):
    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        if not ROUTES_API_KEY:
            raise ProviderConfigurationError("ROUTES_API_KEY não configurada para o provedor Google Routes.")

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
            "routingPreference": "TRAFFIC_UNAWARE",
            "computeAlternativeRoutes": False,
            "languageCode": "pt-BR",
            "units": "METRIC",
        }
        request = Request(
            f"{ROUTES_API_BASE_URL}/directions/v2:computeRoutes",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": ROUTES_API_KEY,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RouteCalculationError(f"Falha ao consultar o Google Routes: {exc}") from exc

        routes = data.get("routes") or []
        if not routes:
            raise RouteCalculationError()

        route = routes[0]
        duration_seconds = int(route.get("duration", "0s").replace("s", "") or 0)
        distance_meters = int(route.get("distanceMeters", 0))
        geometry = decode_google_polyline((route.get("polyline") or {}).get("encodedPolyline", ""))
        return {
            "distancia_metros": distance_meters,
            "distancia_km": round(distance_meters / 1000, 2),
            "duracao_segundos": duration_seconds,
            "duracao_formatada": format_duration(duration_seconds),
            "geometria_preview": simplify_route_coordinates(geometry),
            "rodovias_referencia": [],
            "provedor": "google_routes",
            "dados_brutos": route,
        }


def build_routing_provider():
    if ROUTING_PROVIDER == "osrm":
        return OsrmRoutingProvider()
    if ROUTING_PROVIDER == "google_routes":
        return GoogleRoutesProvider()
    raise ProviderConfigurationError(f'Provedor de rotas "{ROUTING_PROVIDER}" não suportado.')


class RoutingService:
    def __init__(self, provider=None):
        self.provider = provider or build_routing_provider()

    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        return self.provider.calculate_route(origin=origin, destination=destination, payload=payload)
