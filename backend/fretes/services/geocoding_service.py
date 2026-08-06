from __future__ import annotations

import json
import hashlib
import unicodedata
from abc import ABC, abstractmethod
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache

from fretes.constants import GEOCODING_PROVIDER, HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT, NOMINATIM_BASE_URL
from fretes.exceptions import GeocodingError, ProviderConfigurationError
from fretes.utils.validators import build_location_query


def build_geocoding_cache_key(city: str, state: str = "") -> str:
    location = unicodedata.normalize("NFKC", f"{city.strip()}|{state.strip()}").casefold()
    digest = hashlib.sha256(location.encode("utf-8")).hexdigest()
    return f"fretes:geocode:v1:{digest}"


class BaseGeocodingProvider(ABC):
    @abstractmethod
    def geocode(self, city: str, state: str = "", target: str = "origem") -> dict:
        raise NotImplementedError

    @abstractmethod
    def reverse_geocode(self, lat: float, lng: float) -> dict:
        raise NotImplementedError


class NominatimGeocodingProvider(BaseGeocodingProvider):
    def geocode(self, city: str, state: str = "", target: str = "origem") -> dict:
        query = build_location_query(city, state)
        params = urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "br",
                "addressdetails": 1,
            }
        )
        request = Request(
            f"{NOMINATIM_BASE_URL}/search?{params}",
            headers={"User-Agent": HTTP_USER_AGENT},
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GeocodingError(target=target, message=f"Falha ao consultar o provedor de geocodificação: {exc}") from exc

        if not payload:
            raise GeocodingError(target=target)

        result = payload[0]
        address = result.get("address", {})
        resolved_city = address.get("city") or address.get("town") or address.get("municipality") or city
        resolved_state = address.get("state_code") or state or ""

        return {
            "cidade": resolved_city,
            "estado": resolved_state.upper(),
            "coordenadas": {
                "lat": float(result["lat"]),
                "lng": float(result["lon"]),
            },
            "provedor": "nominatim",
        }

    def reverse_geocode(self, lat: float, lng: float) -> dict:
        params = urlencode(
            {
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 10,
            }
        )
        request = Request(
            f"{NOMINATIM_BASE_URL}/reverse?{params}",
            headers={"User-Agent": HTTP_USER_AGENT},
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return {}

        address = payload.get("address", {})
        city = address.get("city") or address.get("town") or address.get("municipality") or address.get("county")
        state = address.get("state_code") or ""
        if not city:
            return {}
        return {"cidade": city, "estado": state.upper()}


def build_geocoding_provider():
    if GEOCODING_PROVIDER == "nominatim":
        return NominatimGeocodingProvider()
    raise ProviderConfigurationError(f'Provedor de geocodificação "{GEOCODING_PROVIDER}" não suportado.')


class GeocodingService:
    def __init__(self, provider=None):
        self.provider = provider or build_geocoding_provider()

    def geocode(self, city: str, state: str = "", target: str = "origem") -> dict:
        cache_key = build_geocoding_cache_key(city, state)
        cached = cache.get(cache_key)
        if cached:
            return cached
        result = self.provider.geocode(city=city, state=state, target=target)
        cache.set(cache_key, result, timeout=60 * 60 * 24 * 30)
        return result

    def reverse_geocode(self, lat: float, lng: float) -> dict:
        return self.provider.reverse_geocode(lat=lat, lng=lng)
