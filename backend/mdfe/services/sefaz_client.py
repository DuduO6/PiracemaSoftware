from dataclasses import dataclass

import requests
from django.conf import settings
from lxml import etree

from .certificate_service import load_configuration_material, tls_certificate_files
from .exceptions import MdfeCommunicationError, MdfeConfigurationError, MdfeError
from .validators import UF_CODES
from .xml_service import build_soap_envelope, secure_parse, serialize


ENDPOINTS = {
    "HOMOLOGACAO": {
        "MDFeConsNaoEnc": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx",
        "MDFeConsulta": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx",
        "MDFeRecepcaoEvento": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx",
    },
    "PRODUCAO": {
        "MDFeConsNaoEnc": "https://mdfe.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx",
        "MDFeConsulta": "https://mdfe.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx",
        "MDFeRecepcaoEvento": "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx",
    },
}
METHODS = {
    "MDFeConsNaoEnc": "mdfeConsNaoEnc",
    "MDFeConsulta": "mdfeConsultaMDF",
    "MDFeRecepcaoEvento": "mdfeRecepcaoEvento",
}


@dataclass
class SefazResponse:
    xml: bytes
    root: etree._Element


class SefazClient:
    def __init__(self, configuration):
        self.configuration = configuration
        if configuration.ambiente == "PRODUCAO" and not (
            settings.MDFE_ENABLE_PRODUCTION and configuration.producao_liberada
        ):
            raise MdfeConfigurationError(
                "Operações MDF-e em produção não estão liberadas.", code="production_not_enabled"
            )
        self.material = load_configuration_material(configuration)

    def send(self, service_name, payload, *, uf_code=None):
        method = METHODS[service_name]
        service_ns = f"http://www.portalfiscal.inf.br/mdfe/wsdl/{service_name}"
        action = f"{service_ns}/{method}"
        envelope = build_soap_envelope(
            payload,
            service_name=service_name,
            uf_code=uf_code or UF_CODES[self.configuration.uf],
        )
        body = serialize(envelope)
        headers = {
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{action}"',
            "Accept": "application/soap+xml, application/xml",
            "User-Agent": "PiracemaSoftware-MDFe/1.0",
        }
        verify = settings.MDFE_CA_BUNDLE
        if not verify:
            raise MdfeConfigurationError("Configure MDFE_CA_BUNDLE.", code="ca_bundle_missing")
        with tls_certificate_files(self.material) as certificate:
            try:
                response = requests.post(
                    ENDPOINTS[self.configuration.ambiente][service_name],
                    data=body,
                    headers=headers,
                    cert=certificate,
                    verify=verify,
                    timeout=(settings.MDFE_CONNECT_TIMEOUT_SECONDS, settings.MDFE_READ_TIMEOUT_SECONDS),
                )
                response.raise_for_status()
            except requests.exceptions.SSLError as exc:
                raise MdfeCommunicationError(
                    "Falha na autenticação TLS com a SEFAZ.", code="sefaz_tls_error"
                ) from exc
            except requests.exceptions.Timeout as exc:
                raise MdfeCommunicationError(
                    "Tempo limite excedido na comunicação com a SEFAZ.", code="sefaz_timeout", inconclusive=True
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise MdfeCommunicationError("Serviço da SEFAZ indisponível.") from exc

        root = secure_parse(response.content)
        fault = root.find(".//{http://www.w3.org/2003/05/soap-envelope}Fault")
        if fault is not None:
            reason = fault.findtext(".//{http://www.w3.org/2003/05/soap-envelope}Text") or "Falha SOAP da SEFAZ."
            raise MdfeCommunicationError(reason, code="sefaz_soap_fault")
        return SefazResponse(response.content, root)


def find_mdfe_payload(response_root, local_name):
    values = response_root.xpath(f"//*[local-name()='{local_name}']")
    if not values:
        raise MdfeError("Resposta inesperada da SEFAZ.", code="unexpected_sefaz_response", status_code=502)
    return values[0]


def child_text(element, local_name, default=""):
    values = element.xpath(f".//*[local-name()='{local_name}']/text()")
    return str(values[0]).strip() if values else default
