from __future__ import annotations

import json
from functools import lru_cache
from urllib.request import Request, urlopen

from fretes.constants import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT, IBGE_MUNICIPIOS_BASE_URL
from fretes.exceptions import FretesError
from fretes.utils.validators import normalize_text


class MunicipalitiesServiceError(FretesError):
    default_message = "Não foi possível carregar a lista de municípios."

    def __init__(self, message=None):
        super().__init__(message=message or self.default_message, code="municipalities_error", status_code=503)


class MunicipalitiesService:
    @lru_cache(maxsize=1)
    def _load_all(self):
        request = Request(
            f"{IBGE_MUNICIPIOS_BASE_URL}/api/v1/localidades/municipios",
            headers={"User-Agent": HTTP_USER_AGENT},
        )
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise MunicipalitiesServiceError(f"Falha ao consultar municípios no IBGE: {exc}") from exc

        municipios = []
        for item in payload:
            uf = item.get("microrregiao", {}).get("mesorregiao", {}).get("UF", {})
            municipio = {
                "id": item.get("id"),
                "cidade": item.get("nome", ""),
                "estado": uf.get("sigla", ""),
                "estado_nome": uf.get("nome", ""),
                "label": f'{item.get("nome", "")} - {uf.get("sigla", "")}',
            }
            municipios.append(municipio)

        municipios.sort(key=lambda item: item["label"])
        return municipios

    def search(self, query: str, limit: int = 20):
        term = normalize_text(query).lower()
        if len(term) < 2:
            return []

        results = []
        for municipio in self._load_all():
            cidade = municipio["cidade"].lower()
            label = municipio["label"].lower()
            if term in cidade or term in label:
                results.append(municipio)
            if len(results) >= limit:
                break
        return results
