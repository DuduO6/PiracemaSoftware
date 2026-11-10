import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from lxml import etree

from .exceptions import MdfeError
from .validators import UF_CODES


MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
SOAP_NS = "http://www.w3.org/2003/05/soap-envelope"
VERSION = "3.00"
EVENT_TYPE = "110112"


def qname(namespace, name):
    return etree.QName(namespace, name)


def _element(parent, name, text=None, *, namespace=MDFE_NS, **attributes):
    element = etree.SubElement(parent, qname(namespace, name), **attributes)
    if text is not None:
        element.text = str(text)
    return element


def secure_parse(value):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False, remove_blank_text=False)
    try:
        return etree.fromstring(value, parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise MdfeError("A SEFAZ retornou um XML inválido.", code="invalid_sefaz_xml", status_code=502) from exc


def serialize(element, declaration=True):
    return etree.tostring(element, encoding="utf-8", xml_declaration=declaration, pretty_print=False)


def build_non_closed_query(configuration):
    root = etree.Element(qname(MDFE_NS, "consMDFeNaoEnc"), nsmap={None: MDFE_NS}, versao=VERSION)
    _element(root, "tpAmb", "1" if configuration.ambiente == "PRODUCAO" else "2")
    _element(root, "xServ", "CONSULTAR NÃO ENCERRADOS")
    _element(root, "CNPJ", configuration.cnpj)
    validate_schema(root, "consMDFeNaoEnc_v3.00.xsd")
    return root


def build_status_query(configuration, access_key):
    root = etree.Element(qname(MDFE_NS, "consSitMDFe"), nsmap={None: MDFE_NS}, versao=VERSION)
    _element(root, "tpAmb", "1" if configuration.ambiente == "PRODUCAO" else "2")
    _element(root, "xServ", "CONSULTAR")
    _element(root, "chMDFe", access_key)
    validate_schema(root, "consSitMDFe_v3.00.xsd")
    return root


def build_closing_event(configuration, manifesto, *, uf, municipality_code, closing_date, event_time, material):
    event_id = f"ID{EVENT_TYPE}{manifesto.chave}01"
    root = etree.Element(qname(MDFE_NS, "eventoMDFe"), nsmap={None: MDFE_NS}, versao=VERSION)
    info = _element(root, "infEvento", Id=event_id)
    _element(info, "cOrgao", manifesto.chave[:2])
    _element(info, "tpAmb", "1" if configuration.ambiente == "PRODUCAO" else "2")
    _element(info, "CNPJ", manifesto.cnpj_emitente)
    _element(info, "chMDFe", manifesto.chave)
    _element(info, "dhEvento", event_time.isoformat(timespec="seconds"))
    _element(info, "tpEvento", EVENT_TYPE)
    _element(info, "nSeqEvento", "1")
    details = _element(info, "detEvento", versaoEvento=VERSION)
    closing = _element(details, "evEncMDFe")
    _element(closing, "descEvento", "Encerramento")
    _element(closing, "nProt", manifesto.protocolo_autorizacao)
    _element(closing, "dtEnc", closing_date.isoformat())
    _element(closing, "cUF", UF_CODES[uf])
    _element(closing, "cMun", municipality_code)

    validate_schema(closing, "evEncMDFe_v3.00.xsd")
    sign_element(root, info, event_id, material)
    validate_schema(root, "eventoMDFe_v3.00.xsd")
    return root, event_id


def sign_element(root, target, identifier, material):
    signature = etree.SubElement(root, qname(DS_NS, "Signature"), nsmap={"ds": DS_NS})
    signed_info = _element(signature, "SignedInfo", namespace=DS_NS)
    _element(
        signed_info,
        "CanonicalizationMethod",
        namespace=DS_NS,
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    _element(
        signed_info,
        "SignatureMethod",
        namespace=DS_NS,
        Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1",
    )
    reference = _element(signed_info, "Reference", namespace=DS_NS, URI=f"#{identifier}")
    transforms = _element(reference, "Transforms", namespace=DS_NS)
    _element(
        transforms,
        "Transform",
        namespace=DS_NS,
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    _element(
        transforms,
        "Transform",
        namespace=DS_NS,
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    _element(
        reference,
        "DigestMethod",
        namespace=DS_NS,
        Algorithm="http://www.w3.org/2000/09/xmldsig#sha1",
    )
    canonical_target = _canonicalize_standalone(target)
    _element(
        reference,
        "DigestValue",
        base64.b64encode(hashlib.sha1(canonical_target).digest()).decode("ascii"),
        namespace=DS_NS,
    )
    canonical_info = _canonicalize_standalone(signed_info)
    signature_value = material.private_key.sign(canonical_info, padding.PKCS1v15(), hashes.SHA1())
    _element(signature, "SignatureValue", base64.b64encode(signature_value).decode("ascii"), namespace=DS_NS)
    key_info = _element(signature, "KeyInfo", namespace=DS_NS)
    x509_data = _element(key_info, "X509Data", namespace=DS_NS)
    certificate_der = material.certificate.public_bytes(serialization.Encoding.DER)
    _element(
        x509_data,
        "X509Certificate",
        base64.b64encode(certificate_der).decode("ascii"),
        namespace=DS_NS,
    )


def _canonicalize_standalone(node):
    # libxml2 pode carregar declarações de namespace inconsistentes do contexto ancestral
    # quando canonicaliza diretamente uma subárvore. Serializar e analisar a subárvore antes
    # do C14N é a mesma normalização usada pelo SignXML e evita xmlns="" espúrios.
    standalone = etree.fromstring(etree.tostring(node))
    return etree.tostring(standalone, method="c14n", exclusive=False, with_comments=False)


def build_soap_envelope(payload, *, service_name, uf_code):
    service_ns = f"http://www.portalfiscal.inf.br/mdfe/wsdl/{service_name}"
    envelope = etree.Element(qname(SOAP_NS, "Envelope"), nsmap={"soap12": SOAP_NS})
    header = etree.SubElement(envelope, qname(SOAP_NS, "Header"))
    soap_header = etree.SubElement(header, qname(service_ns, "mdfeCabecMsg"), nsmap={None: service_ns})
    _element(soap_header, "cUF", uf_code, namespace=service_ns)
    _element(soap_header, "versaoDados", VERSION, namespace=service_ns)
    body = etree.SubElement(envelope, qname(SOAP_NS, "Body"))
    data = etree.SubElement(body, qname(service_ns, "mdfeDadosMsg"), nsmap={None: service_ns})
    data.append(payload)
    return envelope


def schema_path(filename):
    return Path(settings.BASE_DIR) / "mdfe" / "schemas" / filename


def validate_schema(element, filename):
    path = schema_path(filename)
    if not path.is_file():
        raise MdfeConfigurationError(f"Schema oficial ausente: {filename}", code="schema_missing")
    try:
        schema = etree.XMLSchema(etree.parse(str(path)))
        schema.assertValid(element)
    except (etree.XMLSchemaParseError, etree.DocumentInvalid) as exc:
        details = str(exc.error_log.last_error or exc)
        raise MdfeError(
            "O XML do MDF-e não atende ao schema oficial.", code="invalid_mdfe_schema", details={"schema": details}
        ) from exc


# Import tardio para evitar ciclo no carregamento do módulo.
from .exceptions import MdfeConfigurationError  # noqa: E402
