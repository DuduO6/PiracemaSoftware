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

GEOCODING_PROVIDER = os.getenv("GEOCODING_PROVIDER", os.getenv("FRETES_GEOCODING_PROVIDER", "nominatim"))
ROUTING_PROVIDER = os.getenv("ROUTE_PROVIDER", os.getenv("FRETES_ROUTING_PROVIDER", "openrouteservice"))

ROUTES_API_BASE_URL = os.getenv("ROUTES_API_BASE_URL", "https://routes.googleapis.com")
ROUTES_API_KEY = os.getenv("ROUTES_API_KEY", "")
TOLL_PROVIDER = os.getenv("TOLL_PROVIDER", "internal")
TOLL_ROUTE_TOLERANCE_METERS = int(os.getenv("TOLL_ROUTE_TOLERANCE_METERS", "200"))
TOLLS_API_BASE_URL = os.getenv("TOLLS_API_BASE_URL", ROUTES_API_BASE_URL)
TOLLS_API_KEY = os.getenv("TOLLS_API_KEY", ROUTES_API_KEY)

NOMINATIM_BASE_URL = os.getenv("FRETES_NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
OSRM_BASE_URL = os.getenv("FRETES_OSRM_BASE_URL", "https://router.project-osrm.org")
OPENROUTESERVICE_BASE_URL = os.getenv("OPENROUTESERVICE_BASE_URL", "https://api.openrouteservice.org")
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY", "")
IBGE_MUNICIPIOS_BASE_URL = os.getenv("FRETES_IBGE_MUNICIPIOS_BASE_URL", "https://servicodados.ibge.gov.br")
