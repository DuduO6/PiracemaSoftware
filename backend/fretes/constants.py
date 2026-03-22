from decimal import Decimal
import os


DEFAULT_QUANTIDADE_EIXOS = 6
DEFAULT_PESO_ESTIMADO_TONELADAS = Decimal("0")
DEFAULT_TIPO_CARGA = "carga_geral"
DEFAULT_PERCENTUAL_LUCRO_ADICIONAL = Decimal("0")

TIPOS_CARGA = (
    ("granel_solido", "Granel sólido"),
    ("granel_liquido", "Granel líquido"),
    ("frigorificada_aquecida", "Frigorificada ou Aquecida"),
    ("conteinerizada", "Conteinerizada"),
    ("carga_geral", "Carga Geral"),
    ("neogranel", "Neogranel"),
    ("perigosa_granel_solido", "Perigosa (granel sólido)"),
    ("perigosa_granel_liquido", "Perigosa (granel líquido)"),
    ("perigosa_frigorificada_aquecida", "Perigosa (frigorificada ou aquecida)"),
    ("perigosa_conteinerizada", "Perigosa (conteinerizada)"),
    ("perigosa_carga_geral", "Perigosa (carga geral)"),
    ("granel_pressurizada", "Carga Granel Pressurizada"),
)

HTTP_TIMEOUT_SECONDS = int(os.getenv("FRETES_HTTP_TIMEOUT", "15"))
HTTP_USER_AGENT = os.getenv("FRETES_HTTP_USER_AGENT", "PiracemaSoftware/1.0")

GEOCODING_PROVIDER = os.getenv("FRETES_GEOCODING_PROVIDER", "nominatim")
ROUTING_PROVIDER = os.getenv("FRETES_ROUTING_PROVIDER", "osrm")

ROUTES_API_BASE_URL = os.getenv("ROUTES_API_BASE_URL", "https://routes.googleapis.com")
ROUTES_API_KEY = os.getenv("ROUTES_API_KEY", "")

NOMINATIM_BASE_URL = os.getenv("FRETES_NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
OSRM_BASE_URL = os.getenv("FRETES_OSRM_BASE_URL", "https://router.project-osrm.org")
IBGE_MUNICIPIOS_BASE_URL = os.getenv("FRETES_IBGE_MUNICIPIOS_BASE_URL", "https://servicodados.ibge.gov.br")
