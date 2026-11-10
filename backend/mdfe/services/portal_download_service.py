import json
from contextlib import ExitStack
from urllib.parse import urlparse

import requests
from django.conf import settings
from lxml import etree

from .certificate_service import load_configuration_material, tls_certificate_files
from .exceptions import MdfeCommunicationError, MdfeConfigurationError, MdfeError
from .xml_import_service import MAX_XML_BYTES


MAX_PORTAL_RESPONSE_BYTES = MAX_XML_BYTES + (2 * 1024 * 1024)


class PortalNacionalMdfeClient:
    """Cliente do download autenticado disponibilizado pelo Portal Nacional do MDF-e.

    O Portal não oferece este download como Web Service de integração. Mantemos todo o
    conhecimento do formulário HTML nesta classe para que uma eventual alteração do portal
    falhe de forma segura, sem afetar a consulta oficial de não encerrados.
    """

    def __init__(self, configuration):
        self.configuration = configuration
        self.url = settings.MDFE_PORTAL_DOWNLOAD_URL
        self.landing_url = "https://dfe-portal.svrs.rs.gov.br/MDFESSL/DownloadXMLDFe"
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or parsed.hostname != "dfe-portal.svrs.rs.gov.br":
            raise MdfeConfigurationError(
                "A URL de download do Portal Nacional do MDF-e é inválida.",
                code="invalid_mdfe_portal_url",
            )
        if configuration.ambiente == "PRODUCAO" and not (
            settings.MDFE_ENABLE_PRODUCTION and configuration.producao_liberada
        ):
            raise MdfeConfigurationError(
                "Operações MDF-e em produção não estão liberadas.", code="production_not_enabled"
            )
        self._stack = None
        self._session = None

    def __enter__(self):
        self._stack = ExitStack()
        material = load_configuration_material(self.configuration)
        certificate = self._stack.enter_context(tls_certificate_files(material))
        self._session = self._stack.enter_context(requests.Session())
        self._session.cert = certificate
        self._session.verify = settings.MDFE_PORTAL_CA_BUNDLE or True
        self._request("GET", self.landing_url)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._stack:
            self._stack.close()
        self._stack = None
        self._session = None

    def _request(self, method, url, **kwargs):
        try:
            response = self._session.request(
                method,
                url,
                timeout=(settings.MDFE_CONNECT_TIMEOUT_SECONDS, settings.MDFE_READ_TIMEOUT_SECONDS),
                allow_redirects=False,
                **kwargs,
            )
            response.raise_for_status()
        except requests.exceptions.SSLError as exc:
            raise MdfeCommunicationError(
                "Falha na autenticação TLS com o Portal Nacional do MDF-e.",
                code="mdfe_portal_tls_error",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise MdfeCommunicationError(
                "Tempo limite excedido ao baixar o XML no Portal Nacional do MDF-e.",
                code="mdfe_portal_timeout",
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise MdfeCommunicationError(
                "O Portal Nacional do MDF-e está indisponível.", code="mdfe_portal_unavailable"
            ) from exc

        if response.is_redirect or urlparse(response.url).hostname != "dfe-portal.svrs.rs.gov.br":
            raise MdfeCommunicationError(
                "O Portal Nacional devolveu um redirecionamento inesperado.",
                code="unexpected_mdfe_portal_redirect",
            )
        content_length = response.headers.get("Content-Length")
        if (content_length and int(content_length) > MAX_PORTAL_RESPONSE_BYTES) or len(response.content) > MAX_PORTAL_RESPONSE_BYTES:
            raise MdfeError(
                "A resposta do Portal Nacional excedeu o tamanho permitido.",
                code="mdfe_portal_response_too_large",
                status_code=502,
            )
        return response

    def download_xml(self, access_key):
        if not self._session:
            raise RuntimeError("Use PortalNacionalMdfeClient como gerenciador de contexto.")
        response = self._request(
            "POST",
            self.url,
            data={
                "sistema": "Mdfe",
                "OrigemSite": "0",
                "Ambiente": "1" if self.configuration.ambiente == "PRODUCAO" else "2",
                "ChaveAcessoDfe": access_key,
            },
        )
        return self._extract_xml(response.content, access_key)

    @staticmethod
    def _extract_xml(content, access_key):
        try:
            source = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MdfeError(
                "O Portal Nacional devolveu uma página com codificação inválida.",
                code="invalid_mdfe_portal_response",
                status_code=502,
            ) from exc

        # Extrai o JSON diretamente dos bytes recebidos. Passar primeiro por um parser HTML
        # poderia normalizar conteúdo pertencente ao XML assinado.
        search_from = 0
        marker = "var stringJson"
        while True:
            start = source.find(marker, search_from)
            if start < 0:
                break
            assignment = source.find("=", start + len(marker))
            search_from = start + len(marker)
            if assignment < 0:
                continue
            try:
                result, _ = json.JSONDecoder().raw_decode(source[assignment + 1:].lstrip())
            except (json.JSONDecodeError, TypeError):
                continue
            xml = result.get("xml") if isinstance(result, dict) else None
            if isinstance(xml, str) and xml.strip():
                xml_bytes = xml.encode("utf-8")
                if len(xml_bytes) > MAX_XML_BYTES:
                    raise MdfeError(
                        "O XML devolvido pelo Portal Nacional excedeu 5 MB.",
                        code="mdfe_xml_too_large",
                        status_code=502,
                    )
                if access_key.encode("ascii") not in xml_bytes:
                    raise MdfeError(
                        "O Portal Nacional devolveu um XML de outra chave.",
                        code="mdfe_portal_key_mismatch",
                        status_code=502,
                    )
                return xml_bytes

        parser = etree.HTMLParser(recover=False, no_network=True, huge_tree=False)
        try:
            document = etree.fromstring(content, parser=parser)
        except (etree.XMLSyntaxError, ValueError) as exc:
            raise MdfeError(
                "O Portal Nacional devolveu uma página inválida.",
                code="invalid_mdfe_portal_response",
                status_code=502,
            ) from exc

        page_text = " ".join(document.xpath("//body//text()"))
        if "IP não autorizado devido múltiplas consultas" in page_text:
            raise MdfeError(
                "O Portal Nacional bloqueou temporariamente novas consultas por excesso de requisições.",
                code="mdfe_portal_rate_limited",
                status_code=429,
            )
        messages = document.xpath(
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' text-danger ')]"
            "[normalize-space()]/text()"
        )
        detail = " ".join(str(value).strip() for value in messages if str(value).strip())
        raise MdfeError(
            (detail or "O XML não foi disponibilizado pelo Portal Nacional do MDF-e.")[:255],
            code="mdfe_xml_not_available",
            status_code=502,
        )
