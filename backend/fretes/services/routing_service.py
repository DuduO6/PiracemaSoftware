from __future__ import annotations

import json
import hashlib
from abc import ABC, abstractmethod
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from fretes.constants import (
    HTTP_TIMEOUT_SECONDS,
    HTTP_USER_AGENT,
    OSRM_BASE_URL,
    OPENROUTESERVICE_API_KEY,
    OPENROUTESERVICE_BASE_URL,
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

    def calculate_matrix(self, locations: list[dict]) -> dict:
        raise NotImplementedError("Este provider não implementa matriz de distâncias.")


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

    def calculate_matrix(self, locations: list[dict]) -> dict:
        coordinates = ";".join(f"{item['coordenadas']['lng']},{item['coordenadas']['lat']}" for item in locations)
        request = Request(
            f"{OSRM_BASE_URL}/table/v1/driving/{coordinates}?annotations=distance,duration",
            headers={"User-Agent": HTTP_USER_AGENT},
        )
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RouteCalculationError(f"Falha ao consultar matriz OSRM: {exc}") from exc
        return {"distancias_metros": data.get("distances", []), "duracoes_segundos": data.get("durations", []), "provedor": "osrm"}


class OpenRouteServiceProvider(BaseRoutingProvider):
    profile = "driving-hgv"

    def _post(self, endpoint: str, body: dict) -> dict:
        if not OPENROUTESERVICE_API_KEY:
            raise ProviderConfigurationError("OPENROUTESERVICE_API_KEY não configurada.")
        request = Request(
            f"{OPENROUTESERVICE_BASE_URL}{endpoint}", data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": OPENROUTESERVICE_API_KEY, "Content-Type": "application/json", "User-Agent": HTTP_USER_AGENT},
        )
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RouteCalculationError(f"Falha ao consultar OpenRouteService: {exc}") from exc

    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        coordinates = [[origin["coordenadas"]["lng"], origin["coordenadas"]["lat"]], [destination["coordenadas"]["lng"], destination["coordenadas"]["lat"]]]
        data = self._post(f"/v2/directions/{self.profile}/geojson", {"coordinates": coordinates, "instructions": False})
        features = data.get("features") or []
        if not features:
            raise RouteCalculationError()
        feature = features[0]
        summary = feature.get("properties", {}).get("summary", {})
        geometry = feature.get("geometry", {}).get("coordinates", [])
        distance = int(round(summary.get("distance", 0)))
        duration = int(round(summary.get("duration", 0)))
        return {"distancia_metros": distance, "distancia_km": round(distance / 1000, 2), "duracao_segundos": duration,
                "duracao_formatada": format_duration(duration), "geometria_preview": simplify_route_coordinates(geometry),
                "rodovias_referencia": [], "provedor": "openrouteservice", "dados_brutos": {"summary": summary}}

    def calculate_matrix(self, locations: list[dict]) -> dict:
        coordinates = [[item["coordenadas"]["lng"], item["coordenadas"]["lat"]] for item in locations]
        data = self._post(f"/v2/matrix/{self.profile}", {"locations": coordinates, "metrics": ["distance", "duration"]})
        return {"distancias_metros": data.get("distances", []), "duracoes_segundos": data.get("durations", []), "provedor": "openrouteservice"}


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
    if ROUTING_PROVIDER == "openrouteservice":
        return OpenRouteServiceProvider() if OPENROUTESERVICE_API_KEY else OsrmRoutingProvider()
    if ROUTING_PROVIDER == "osrm":
        return OsrmRoutingProvider()
    if ROUTING_PROVIDER == "google_routes":
        return GoogleRoutesProvider()
    raise ProviderConfigurationError(f'Provedor de rotas "{ROUTING_PROVIDER}" não suportado.')


class RoutingService:
    def __init__(self, provider=None):
        self.provider = provider or build_routing_provider()

    def calculate_route(self, origin: dict, destination: dict, payload: dict) -> dict:
        provider_name = self.provider.__class__.__name__.replace("RoutingProvider", "").replace("Provider", "").lower()
        key_payload = {"origem": origin.get("coordenadas"), "destino": destination.get("coordenadas"), "provider": provider_name, "perfil": payload.get("tipo_veiculo", "")}
        chave = hashlib.sha256(json.dumps(key_payload, sort_keys=True).encode()).hexdigest()
        RouteCache = apps.get_model("inteligencia_logistica", "RouteCache")
        if getattr(settings, "USE_ROUTE_CACHE", True):
            cached = RouteCache.objects.filter(chave=chave, valido_ate__gt=timezone.now()).first()
            if cached:
                resultado = dict(cached.resposta)
                resultado["cache"] = True
                return resultado
        resultado = self.provider.calculate_route(origin=origin, destination=destination, payload=payload)
        if getattr(settings, "USE_ROUTE_CACHE", True):
            RouteCache.objects.update_or_create(chave=chave, defaults={
                "origem": origin, "destino": destination, "provider": resultado.get("provedor", provider_name),
                "distancia_metros": resultado["distancia_metros"], "tempo_segundos": resultado["duracao_segundos"],
                "pedagios": resultado.get("pedagios", []), "geometria": resultado.get("geometria_preview", []),
                "resposta": resultado, "valido_ate": timezone.now() + timedelta(days=getattr(settings, "ROUTE_CACHE_TTL_DAYS", 30)),
            })
        resultado["cache"] = False
        return resultado

    def calculate_matrix(self, locations: list[dict]) -> dict:
        if len(locations) > 100:
            raise ValueError("A matriz está limitada a 100 locais por consulta.")
        return self.provider.calculate_matrix(locations)


class DistanceMatrixService:
    def __init__(self, routing_service=None):
        self.routing_service = routing_service or RoutingService()

    def calculate(self, locations: list[dict]) -> dict:
        return self.routing_service.calculate_matrix(locations)
