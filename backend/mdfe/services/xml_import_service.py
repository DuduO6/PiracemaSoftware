import base64
import hashlib
import re

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from lxml import etree
from signxml import DigestAlgorithm, SignatureConfiguration, SignatureMethod, XMLVerifier
from signxml.exceptions import InvalidDigest, InvalidSignature, SignXMLException

from inteligencia_logistica.models import MembroEmpresa
from motoristas.models import Motorista

from mdfe.models import Manifesto, ManifestoCondutor

from .certificate_service import certificate_cnpj, encrypt_secret
from .exceptions import MdfeError
from .validators import access_key_data, validate_access_key
from .xml_service import DS_NS, MDFE_NS, validate_schema


MAX_XML_BYTES = 5 * 1024 * 1024

MDFE_SIGNATURE_CONFIGURATION = SignatureConfiguration(
    require_x509=True,
    location=f"./{{{MDFE_NS}}}MDFe/",
    expect_references=1,
    signature_methods=frozenset({SignatureMethod.RSA_SHA1, SignatureMethod.RSA_SHA256}),
    digest_algorithms=frozenset({DigestAlgorithm.SHA1, DigestAlgorithm.SHA256}),
)


def _text(node, name):
    values = node.xpath(f"./*[local-name()='{name}']/text()")
    return str(values[0]).strip() if values else ""


def parse_mdfe_proc_xml(xml_bytes):
    if not xml_bytes or len(xml_bytes) > MAX_XML_BYTES:
        raise MdfeError("O XML deve ter conteúdo e no máximo 5 MB.", code="invalid_mdfe_xml")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False, huge_tree=False)
    try:
        root = etree.fromstring(xml_bytes, parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise MdfeError("O arquivo não contém um XML válido.", code="invalid_mdfe_xml") from exc
    if root.getroottree().docinfo.doctype:
        raise MdfeError("XML com declaração DTD não é permitido.", code="invalid_mdfe_xml")
    if etree.QName(root).namespace != MDFE_NS or etree.QName(root).localname != "mdfeProc":
        raise MdfeError("Envie o XML processado do MDF-e (mdfeProc).", code="invalid_mdfe_xml")
    return root


def _verify_signature(root, info, *, allow_unverified=False):
    identifier = info.get("Id", "")
    if not identifier or not identifier.startswith("MDFe"):
        raise MdfeError("O XML não possui identificador fiscal válido.", code="invalid_mdfe_xml")
    signatures = root.xpath(".//ds:Signature", namespaces={"ds": DS_NS})
    if len(signatures) != 1:
        raise MdfeError("O XML deve conter exatamente uma assinatura digital.", code="invalid_xml_signature")
    signature = signatures[0]
    if etree.QName(signature.getparent()).localname != "MDFe":
        raise MdfeError("A assinatura não está vinculada ao MDF-e.", code="invalid_xml_signature")
    references = signature.xpath("./ds:SignedInfo/ds:Reference", namespaces={"ds": DS_NS})
    if len(references) != 1 or references[0].get("URI") != f"#{identifier}":
        raise MdfeError("A assinatura não referencia o MDF-e importado.", code="invalid_xml_signature")
    try:
        informed_digest = base64.b64decode(
            references[0].xpath("string(./ds:DigestValue)", namespaces={"ds": DS_NS}), validate=True
        )
    except ValueError as exc:
        raise MdfeError("O resumo da assinatura é inválido.", code="invalid_xml_signature") from exc
    certificate_text = signature.xpath("string(.//ds:X509Certificate)", namespaces={"ds": DS_NS})
    try:
        certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_text, validate=True))
    except (ValueError, TypeError) as exc:
        raise MdfeError("O certificado da assinatura é inválido.", code="invalid_xml_signature") from exc
    if not isinstance(certificate.public_key(), rsa.RSAPublicKey):
        raise MdfeError("A assinatura do MDF-e não utiliza chave RSA.", code="invalid_xml_signature")

    try:
        result = XMLVerifier().verify(
            root,
            x509_cert=certificate,
            validate_schema=False,
            id_attribute="Id",
            expect_config=MDFE_SIGNATURE_CONFIGURATION,
        )
    except InvalidDigest as exc:
        if not allow_unverified:
            raise MdfeError(
                "O conteúdo do MDF-e não corresponde ao digest assinado.", code="invalid_xml_digest"
            ) from exc
        return certificate, base64.b64encode(informed_digest).decode("ascii"), False
    except InvalidSignature as exc:
        if not allow_unverified:
            raise MdfeError("A assinatura digital do MDF-e é inválida.", code="invalid_xml_signature") from exc
        return certificate, base64.b64encode(informed_digest).decode("ascii"), False
    except SignXMLException as exc:
        if not allow_unverified:
            raise MdfeError("A estrutura da assinatura digital é inválida.", code="invalid_xml_signature") from exc
        return certificate, base64.b64encode(informed_digest).decode("ascii"), False
    results = result if isinstance(result, list) else [result]
    if len(results) != 1 or results[0].signed_xml.get("Id") != identifier:
        raise MdfeError("A assinatura não protege o MDF-e importado.", code="invalid_xml_signature")
    return certificate, base64.b64encode(informed_digest).decode("ascii"), True


def _normalize_cpf(value):
    cpf = re.sub(r"\D", "", str(value or ""))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        raise MdfeError("O XML contém CPF de condutor inválido.", code="invalid_driver_cpf")
    digits = [int(char) for char in cpf]
    for size, weight_start in ((9, 10), (10, 11)):
        total = sum(digit * weight for digit, weight in zip(digits[:size], range(weight_start, 1, -1)))
        expected = 11 - (total % 11)
        expected = 0 if expected >= 10 else expected
        if digits[size] != expected:
            raise MdfeError("O XML contém CPF de condutor inválido.", code="invalid_driver_cpf")
    return cpf


def _company_drivers(company):
    user_ids = MembroEmpresa.objects.filter(empresa=company, ativo=True).values_list("usuario_id", flat=True)
    drivers = Motorista.objects.filter(usuario_id__in=user_ids)
    return {re.sub(r"\D", "", driver.cpf): driver for driver in drivers}


class MdfeXmlImportService:
    def __init__(self, configuration):
        self.configuration = configuration

    def import_document(self, xml_bytes, *, source=Manifesto.XmlFonte.IMPORTACAO_MANUAL):
        if source not in Manifesto.XmlFonte.values:
            raise MdfeError("Origem do XML inválida.", code="invalid_xml_source")
        root = parse_mdfe_proc_xml(xml_bytes)
        validate_schema(root, "procMDFe_v3.00.xsd")

        info_nodes = root.xpath("./*[local-name()='MDFe']/*[local-name()='infMDFe']")
        protocol_nodes = root.xpath("./*[local-name()='protMDFe']/*[local-name()='infProt']")
        if len(info_nodes) != 1 or len(protocol_nodes) != 1:
            raise MdfeError("Estrutura do MDF-e processado inválida.", code="invalid_mdfe_xml")
        info = info_nodes[0]
        protocol = protocol_nodes[0]
        key = validate_access_key(info.get("Id", "").removeprefix("MDFe"))
        protocol_key = validate_access_key(_text(protocol, "chMDFe"))
        if protocol_key != key:
            raise MdfeError("A chave do protocolo não corresponde ao MDF-e.", code="xml_key_mismatch")

        issuer_nodes = info.xpath("./*[local-name()='emit']/*[local-name()='CNPJ']/text()")
        issuer = str(issuer_nodes[0]).strip().upper() if issuer_nodes else ""
        key_data = access_key_data(key)
        if issuer != key_data["issuer_cnpj"]:
            raise MdfeError("O emitente do XML não corresponde à chave de acesso.", code="xml_issuer_mismatch")
        if issuer[:8] != self.configuration.cnpj[:8]:
            raise MdfeError("O XML pertence a outra raiz de CNPJ.", code="xml_issuer_mismatch")

        expected_environment = "1" if self.configuration.ambiente == "PRODUCAO" else "2"
        environment = info.xpath("string(./*[local-name()='ide']/*[local-name()='tpAmb'])").strip()
        if environment != expected_environment or _text(protocol, "tpAmb") != expected_environment:
            raise MdfeError("O ambiente do XML difere da configuração fiscal.", code="xml_environment_mismatch")
        if _text(protocol, "cStat") != "100":
            raise MdfeError("O XML não contém autorização de uso válida (cStat 100).", code="xml_not_authorized")
        protocol_number = _text(protocol, "nProt")
        if not protocol_number.isdigit() or len(protocol_number) != 15:
            raise MdfeError("O protocolo de autorização do XML é inválido.", code="invalid_sefaz_protocol")

        allow_informational_xml = (
            source == Manifesto.XmlFonte.PORTAL_NACIONAL
            and (
                settings.MDFE_ALLOW_INFORMATIONAL_PORTAL_XML
                or settings.MDFE_ALLOW_UNVERIFIED_PORTAL_XML
            )
        )
        certificate, signed_digest, content_digest_valid = _verify_signature(
            root,
            info,
            allow_unverified=allow_informational_xml,
        )
        signer_cnpj = certificate_cnpj(certificate)
        if not signer_cnpj or signer_cnpj[:8] != issuer[:8]:
            raise MdfeError("O certificado da assinatura não pertence ao emitente.", code="xml_signer_mismatch")
        protocol_digest = _text(protocol, "digVal")
        if not protocol_digest or protocol_digest != signed_digest:
            raise MdfeError("O protocolo não confirma a integridade do XML.", code="xml_protocol_digest_mismatch")

        road_nodes = info.xpath(".//*[local-name()='infModal']/*[local-name()='rodo']")
        if road_nodes:
            validate_schema(road_nodes[0], "mdfeModalRodoviario_v3.00.xsd")
        driver_nodes = info.xpath(
            ".//*[local-name()='infModal']/*[local-name()='rodo']//*[local-name()='condutor']"
        )
        drivers = []
        seen_cpfs = set()
        for node in driver_nodes:
            cpf = _normalize_cpf(_text(node, "CPF"))
            name = _text(node, "xNome")[:150]
            if not name:
                raise MdfeError("O XML contém condutor sem nome.", code="invalid_driver")
            if cpf not in seen_cpfs:
                drivers.append((cpf, name))
                seen_cpfs.add(cpf)

        emitted_at_text = info.xpath("string(./*[local-name()='ide']/*[local-name()='dhEmi'])").strip()
        emitted_at = parse_datetime(emitted_at_text)
        if emitted_at is None:
            raise MdfeError("A data de emissão do XML é inválida.", code="invalid_mdfe_xml")

        destination_uf = info.xpath("string(./*[local-name()='ide']/*[local-name()='UFFim'])").strip()[:2]
        destinations = []
        seen_destinations = set()
        for node in info.xpath("./*[local-name()='infDoc']/*[local-name()='infMunDescarga']"):
            code = _text(node, "cMunDescarga")
            name = _text(node, "xMunDescarga")[:120]
            if not code.isdigit() or len(code) != 7 or not name or code in seen_destinations:
                continue
            destinations.append({"codigo": code, "municipio": name, "uf": destination_uf})
            seen_destinations.add(code)

        with transaction.atomic():
            manifest = Manifesto.objects.select_for_update().filter(
                empresa=self.configuration.empresa, chave=key
            ).first()
            if not manifest:
                raise MdfeError(
                    "Atualize os manifestos na SEFAZ antes de importar o XML.",
                    code="manifest_not_consulted",
                    status_code=409,
                )
            if manifest.protocolo_autorizacao != protocol_number:
                raise MdfeError(
                    "O protocolo do XML difere do protocolo consultado na SEFAZ.",
                    code="xml_protocol_mismatch",
                    status_code=409,
                )
            if manifest.situacao == Manifesto.Situacao.ENCERRADO:
                raise MdfeError(
                    "O XML não é armazenado novamente após o encerramento do MDF-e.",
                    code="manifest_already_closed",
                    status_code=409,
                )

            local_drivers = _company_drivers(self.configuration.empresa)
            manifest.condutores.all().delete()
            for cpf, name in drivers:
                ManifestoCondutor.objects.create(
                    manifesto=manifest,
                    nome_xml=name,
                    cpf=cpf,
                    motorista=local_drivers.get(cpf),
                )
            manifest.numero = key_data["number"]
            manifest.cnpj_emitente = issuer
            manifest.data_emissao = emitted_at
            manifest.xml_importado_em = timezone.now()
            manifest.xml_sha256 = hashlib.sha256(xml_bytes).hexdigest()
            manifest.xml_criptografado = encrypt_secret(xml_bytes)
            manifest.xml_status = Manifesto.XmlStatus.DISPONIVEL
            manifest.xml_fonte = source
            manifest.xml_ultima_tentativa_em = manifest.xml_importado_em
            manifest.xml_ultimo_erro = ""
            manifest.xml_assinatura_conteudo_validada = content_digest_valid
            manifest.xml_classificacao = (
                Manifesto.XmlClassificacao.VERIFICADO
                if content_digest_valid
                else Manifesto.XmlClassificacao.INFORMATIVO
            )
            manifest.destinos = destinations
            manifest.save(update_fields=(
                "numero", "cnpj_emitente", "data_emissao", "xml_importado_em", "xml_sha256",
                "xml_criptografado", "xml_status", "xml_fonte", "xml_ultima_tentativa_em",
                "xml_ultimo_erro", "xml_assinatura_conteudo_validada", "xml_classificacao",
                "destinos", "atualizado_em"
            ))

        linked = sum(1 for cpf, _ in drivers if cpf in local_drivers)
        return {
            "chave": key,
            "numero": key_data["number"],
            "condutores": len(drivers),
            "vinculados": linked,
            "nao_vinculados": len(drivers) - linked,
            "destinos": destinations,
            "assinatura_conteudo_validada": content_digest_valid,
            "classificacao": manifest.xml_classificacao,
        }
