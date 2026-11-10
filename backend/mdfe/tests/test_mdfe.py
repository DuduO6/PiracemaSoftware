import base64
from datetime import date, datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch
import json

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from lxml import etree
from rest_framework.test import APIClient

from inteligencia_logistica.models import Empresa, MembroEmpresa
from mdfe.models import ConfiguracaoFiscal, ConsultaManifestos, Manifesto, ManifestoCondutor, OperacaoEncerramento
from motoristas.models import Motorista
from mdfe.services.certificate_service import certificate_metadata, decrypt_secret, encrypt_secret, load_pkcs12
from mdfe.services.consulta_service import ConsultaMdfeService, DocumentStatus
from mdfe.services.encerramento_service import EncerramentoMdfeService
from mdfe.services.exceptions import MdfeCommunicationError, MdfeError
from mdfe.services.sefaz_client import SefazResponse
from mdfe.services.portal_download_service import PortalNacionalMdfeClient
from mdfe.services.xml_service import MDFE_NS, build_closing_event, secure_parse, sign_element
from mdfe.services.xml_import_service import MdfeXmlImportService


FERNET_KEY = "K9rDFqrgloA_Y0_ZWzZRxfZW4Gy1VWxPGqQqozbEphg="
CNPJ = "12345678000195"


def der_utf8(value):
    raw = value.encode("utf-8")
    return bytes((0x0C, len(raw))) + raw


def certificate_pfx(cnpj=CNPJ, *, expired=False, password="senha-forte"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(dt_timezone.utc)
    start = now - timedelta(days=60 if expired else 1)
    end = now - timedelta(days=1) if expired else now + timedelta(days=365)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Transportadora Teste"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Certificado Teste A1"),
    ])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(end)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=True, key_encipherment=True,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=None, decipher_only=None,
            ), critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .add_extension(
            x509.SubjectAlternativeName([
                x509.OtherName(ObjectIdentifier("2.16.76.1.3.3"), der_utf8(cnpj)),
            ]), critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"mdfe-test", key, certificate, None,
        serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    return pfx, key, certificate


def access_key(number=123, numeric_code=12345678):
    base = f"312611{CNPJ}58001{number:09d}1{numeric_code:08d}"
    total = sum(int(digit) * weight for digit, weight in zip(reversed(base), [2, 3, 4, 5, 6, 7, 8, 9] * 6))
    remainder = total % 11
    digit = 0 if remainder in (0, 1) else 11 - remainder
    return base + str(digit)


def non_closed_xml(items=(), code="111", reason="Consulta realizada"):
    rows = "".join(f"<infMDFe><chMDFe>{key}</chMDFe><nProt>{protocol}</nProt></infMDFe>" for key, protocol in items)
    return f'''<retConsMDFeNaoEnc xmlns="http://www.portalfiscal.inf.br/mdfe" versao="3.00"><tpAmb>2</tpAmb><verAplic>TESTE</verAplic><cStat>{code}</cStat><xMotivo>{reason}</xMotivo><cUF>31</cUF>{rows}</retConsMDFeNaoEnc>'''.encode()


def event_xml(code="135", reason="Evento registrado e vinculado ao MDF-e", protocol="935260000000001"):
    optional = f"<chMDFe>{access_key()}</chMDFe><tpEvento>110112</tpEvento><xEvento>Encerramento</xEvento><nSeqEvento>1</nSeqEvento><dhRegEvento>2026-11-10T10:00:00-03:00</dhRegEvento><nProt>{protocol}</nProt>" if protocol else ""
    return f'''<retEventoMDFe xmlns="http://www.portalfiscal.inf.br/mdfe" versao="3.00"><infEvento><tpAmb>2</tpAmb><verAplic>TESTE</verAplic><cOrgao>31</cOrgao><cStat>{code}</cStat><xMotivo>{reason}</xMotivo>{optional}</infEvento></retEventoMDFe>'''.encode()


def status_xml_with_direct_event():
    event = event_xml().decode("utf-8")
    return f'''<retConsSitMDFe xmlns="http://www.portalfiscal.inf.br/mdfe" versao="3.00"><tpAmb>2</tpAmb><verAplic>TESTE</verAplic><cStat>132</cStat><xMotivo>MDF-e encerrado</xMotivo><cUF>31</cUF>{event}</retConsSitMDFe>'''.encode()


def processed_mdfe_xml(key, private_key, certificate, *, driver_name="João da Silva", driver_cpf="52998224725", protocol="935260000000000"):
    qname = lambda name: etree.QName(MDFE_NS, name)
    root = etree.Element(qname("mdfeProc"), nsmap={None: MDFE_NS}, versao="3.00")
    mdfe = etree.SubElement(root, qname("MDFe"))
    identifier = f"MDFe{key}"
    info = etree.SubElement(mdfe, qname("infMDFe"), Id=identifier, versao="3.00")
    ide = etree.SubElement(info, qname("ide"))
    etree.SubElement(ide, qname("tpAmb")).text = "2"
    etree.SubElement(ide, qname("dhEmi")).text = "2026-11-10T10:00:00-03:00"
    etree.SubElement(ide, qname("UFFim")).text = "MG"
    emit = etree.SubElement(info, qname("emit"))
    etree.SubElement(emit, qname("CNPJ")).text = CNPJ
    modal = etree.SubElement(info, qname("infModal"))
    road = etree.SubElement(modal, qname("rodo"))
    traction = etree.SubElement(road, qname("veicTracao"))
    driver = etree.SubElement(traction, qname("condutor"))
    etree.SubElement(driver, qname("xNome")).text = driver_name
    etree.SubElement(driver, qname("CPF")).text = driver_cpf
    documents = etree.SubElement(info, qname("infDoc"))
    destination = etree.SubElement(documents, qname("infMunDescarga"))
    etree.SubElement(destination, qname("cMunDescarga")).text = "3106200"
    etree.SubElement(destination, qname("xMunDescarga")).text = "Belo Horizonte"

    material = SimpleNamespace(private_key=private_key, certificate=certificate)
    sign_element(mdfe, info, identifier, material)
    digest = mdfe.xpath("string(.//*[local-name()='DigestValue'])")

    protocol_root = etree.SubElement(root, qname("protMDFe"), versao="3.00")
    protocol_info = etree.SubElement(protocol_root, qname("infProt"), Id=f"MDFe{protocol}")
    etree.SubElement(protocol_info, qname("tpAmb")).text = "2"
    etree.SubElement(protocol_info, qname("verAplic")).text = "TESTE"
    etree.SubElement(protocol_info, qname("chMDFe")).text = key
    etree.SubElement(protocol_info, qname("dhRecbto")).text = "2026-11-10T10:01:00-03:00"
    etree.SubElement(protocol_info, qname("nProt")).text = protocol
    etree.SubElement(protocol_info, qname("digVal")).text = digest
    etree.SubElement(protocol_info, qname("cStat")).text = "100"
    etree.SubElement(protocol_info, qname("xMotivo")).text = "Autorizado o uso do MDF-e"
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


@override_settings(MDFE_ENCRYPTION_KEY=FERNET_KEY, MDFE_ENABLE_PRODUCTION=False)
class MdfeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin-mdfe", "admin-mdfe@example.com", "senha-forte")
        self.operator = User.objects.create_user("operador-mdfe", "op-mdfe@example.com", "senha-forte")
        self.reader = User.objects.create_user("leitor-mdfe", "reader-mdfe@example.com", "senha-forte")
        self.other = User.objects.create_user("outro-mdfe", "other-mdfe@example.com", "senha-forte")
        self.company = Empresa.objects.create(nome="Transportadora Teste", slug="transportadora-teste-mdfe")
        MembroEmpresa.objects.create(empresa=self.company, usuario=self.admin, papel="ADMIN")
        MembroEmpresa.objects.create(empresa=self.company, usuario=self.operator, papel="OPERADOR")
        MembroEmpresa.objects.create(empresa=self.company, usuario=self.reader, papel="LEITURA")
        pfx, self.signing_key, self.signing_certificate = certificate_pfx()
        material = load_pkcs12(pfx, "senha-forte", expected_cnpj=CNPJ)
        metadata = certificate_metadata(material)
        self.configuration = ConfiguracaoFiscal.objects.create(
            empresa=self.company, razao_social="Transportadora Teste Ltda", cnpj=CNPJ, uf="MG",
            ambiente="HOMOLOGACAO", certificado_criptografado=encrypt_secret(pfx),
            senha_criptografada=encrypt_secret(b"senha-forte"), certificado_nome="teste.pfx",
            certificado_fingerprint=metadata["fingerprint"], certificado_cnpj=metadata["cnpj"],
            certificado_valido_de=metadata["valid_from"], certificado_valido_ate=metadata["valid_until"],
            atualizado_por=self.admin,
        )
        self.manifest = Manifesto.objects.create(
            empresa=self.company, chave=access_key(), numero="000000123", cnpj_emitente=CNPJ,
            protocolo_autorizacao="935260000000000", situacao="ABERTO", ultima_consulta_em=timezone.now(),
        )
        self.client = APIClient()

    def sefaz_response(self, xml):
        return SefazResponse(xml=xml, root=secure_parse(xml))

    def test_rejeita_cnpj_invalido(self):
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            "/api/mdfe/configuracao/",
            {"razao_social": "Teste", "cnpj": "11111111111111", "uf": "MG", "ambiente": "HOMOLOGACAO"},
            format="multipart", HTTP_X_EMPRESA_ID=self.company.id,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_cnpj")

    def test_rejeita_certificado_expirado(self):
        pfx, _, _ = certificate_pfx(expired=True)
        with self.assertRaises(MdfeError) as context:
            load_pkcs12(pfx, "senha-forte", expected_cnpj=CNPJ)
        self.assertEqual(context.exception.code, "expired_certificate")

    def test_rejeita_certificado_de_outro_contribuinte(self):
        pfx, _, _ = certificate_pfx("98765432000198")
        with self.assertRaises(MdfeError) as context:
            load_pkcs12(pfx, "senha-forte", expected_cnpj=CNPJ)
        self.assertEqual(context.exception.code, "certificate_cnpj_mismatch")

    @patch("mdfe.services.consulta_service.SefazClient")
    def test_consulta_sem_manifestos(self, client_class):
        client_class.return_value.send.return_value = self.sefaz_response(non_closed_xml((), "112", "Não existem MDF-e não encerrados"))
        audit = ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)
        self.assertEqual(audit.quantidade, 0)
        self.assertEqual(audit.codigo_sefaz, "112")

    @patch("mdfe.services.consulta_service.ConsultaMdfeService._hydrate_xmls", return_value={"downloaded": 0, "cached": 0, "errors": 0})
    @patch("mdfe.services.consulta_service.SefazClient")
    def test_consulta_com_multiplos_manifestos(self, client_class, _hydrate):
        other = access_key(124, 87654321)
        client_class.return_value.send.return_value = self.sefaz_response(non_closed_xml([
            (access_key(), "935260000000000"), (other, "935260000000002"),
        ]))
        audit = ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)
        self.assertEqual(audit.quantidade, 2)
        self.assertEqual(Manifesto.objects.filter(empresa=self.company, situacao="ABERTO").count(), 2)

    @patch("mdfe.services.xml_import_service.validate_schema")
    @patch("mdfe.services.consulta_service.PortalNacionalMdfeClient")
    @patch("mdfe.services.consulta_service.SefazClient")
    def test_atualizacao_baixa_xml_uma_vez_e_reutiliza_cache(self, sefaz_class, portal_class, _schema):
        sefaz_class.return_value.send.return_value = self.sefaz_response(non_closed_xml([
            (access_key(), "935260000000000"),
        ]))
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        portal = portal_class.return_value.__enter__.return_value
        portal.download_xml.return_value = xml

        first = ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)
        second = ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)

        self.manifest.refresh_from_db()
        self.assertEqual(first.xml_baixados, 1)
        self.assertEqual(second.xml_em_cache, 1)
        self.assertEqual(portal.download_xml.call_count, 1)
        self.assertEqual(portal_class.call_count, 1)
        self.assertEqual(self.manifest.xml_status, Manifesto.XmlStatus.DISPONIVEL)
        self.assertEqual(self.manifest.xml_fonte, Manifesto.XmlFonte.PORTAL_NACIONAL)
        self.assertNotEqual(bytes(self.manifest.xml_criptografado), xml)
        self.assertEqual(decrypt_secret(self.manifest.xml_criptografado), xml)
        self.assertEqual(self.manifest.destinos[0]["municipio"], "Belo Horizonte")
        self.assertEqual(self.manifest.condutores.get().nome_xml, "João da Silva")

    @patch("mdfe.services.consulta_service.PortalNacionalMdfeClient")
    @patch("mdfe.services.consulta_service.SefazClient")
    def test_falha_no_xml_nao_descarta_consulta_de_manifestos(self, sefaz_class, portal_class):
        sefaz_class.return_value.send.return_value = self.sefaz_response(non_closed_xml([
            (access_key(), "935260000000000"),
        ]))
        portal_class.return_value.__enter__.return_value.download_xml.side_effect = MdfeCommunicationError(
            "Portal temporariamente indisponível"
        )

        audit = ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)

        self.manifest.refresh_from_db()
        self.assertEqual(audit.estado, ConsultaManifestos.Estado.SUCESSO)
        self.assertEqual(audit.xml_erros, 1)
        self.assertEqual(self.manifest.situacao, Manifesto.Situacao.ABERTO)
        self.assertEqual(self.manifest.xml_status, Manifesto.XmlStatus.ERRO)

    def test_parser_do_portal_extrai_json_sem_executar_javascript(self):
        xml = b'<mdfeProc xmlns="http://www.portalfiscal.inf.br/mdfe">' + access_key().encode() + b'</mdfeProc>'
        page = (
            "<html><script>var stringJson = "
            + json.dumps({"xml": xml.decode()})
            + "; function downloadXml(){}</script></html>"
        ).encode()
        self.assertEqual(PortalNacionalMdfeClient._extract_xml(page, access_key()), xml)

    @override_settings(
        MDFE_ALLOW_INFORMATIONAL_PORTAL_XML=True,
        MDFE_ALLOW_UNVERIFIED_PORTAL_XML=False,
    )
    @patch("mdfe.services.xml_import_service.validate_schema")
    def test_modo_informativo_aceita_apenas_xml_do_portal_sem_digest_valido(self, _schema):
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        changed = xml.replace("João da Silva".encode(), "João de Souza".encode())
        service = MdfeXmlImportService(self.configuration)

        result = service.import_document(changed, source=Manifesto.XmlFonte.PORTAL_NACIONAL)

        self.manifest.refresh_from_db()
        self.assertFalse(result["assinatura_conteudo_validada"])
        self.assertEqual(result["classificacao"], Manifesto.XmlClassificacao.INFORMATIVO)
        self.assertFalse(self.manifest.xml_assinatura_conteudo_validada)
        self.assertEqual(self.manifest.xml_classificacao, Manifesto.XmlClassificacao.INFORMATIVO)
        self.assertEqual(self.manifest.xml_status, Manifesto.XmlStatus.DISPONIVEL)
        self.client.force_authenticate(self.reader)
        listing = self.client.get("/api/mdfe/pendentes/", HTTP_X_EMPRESA_ID=self.company.id)
        serialized = listing.data["results"]["items"][0]
        self.assertTrue(serialized["xml_somente_informativo"])
        self.assertEqual(serialized["xml_classificacao_display"], "Somente informativo")
        self.assertEqual(serialized["xml_sha256"], self.manifest.xml_sha256)
        with self.assertRaises(MdfeError) as context:
            service.import_document(changed, source=Manifesto.XmlFonte.IMPORTACAO_MANUAL)
        self.assertEqual(context.exception.code, "invalid_xml_digest")

    def test_resposta_xml_invalida(self):
        with self.assertRaises(MdfeError) as context:
            secure_parse(b"<xml><invalido>")
        self.assertEqual(context.exception.code, "invalid_sefaz_xml")

    @patch("mdfe.services.consulta_service.SefazClient")
    def test_falha_de_comunicacao_preserva_cache(self, client_class):
        client_class.return_value.send.side_effect = MdfeCommunicationError("Indisponível")
        with self.assertRaises(MdfeError):
            ConsultaMdfeService(self.configuration).refresh_non_closed(self.operator)
        self.manifest.refresh_from_db()
        self.assertEqual(self.manifest.situacao, "ABERTO")
        self.assertEqual(ConsultaManifestos.objects.first().estado, "ERRO")

    @patch("mdfe.services.consulta_service.SefazClient")
    def test_consulta_aceita_retorno_de_evento_direto_da_svrs(self, client_class):
        client_class.return_value.send.return_value = self.sefaz_response(status_xml_with_direct_event())

        result = ConsultaMdfeService(self.configuration).document_status(self.manifest.chave)

        self.assertEqual(result.code, "132")
        self.assertEqual(result.closing_protocol, "935260000000001")
        self.assertEqual(result.closing_datetime, "2026-11-10T10:00:00-03:00")

    @patch("mdfe.services.encerramento_service.SefazClient")
    @patch("mdfe.services.consulta_service.SefazClient")
    def test_encerramento_ja_registrado_na_svrs_nao_e_retransmitido(self, status_client, event_client):
        status_client.return_value.send.return_value = self.sefaz_response(status_xml_with_direct_event())

        operation = EncerramentoMdfeService(self.configuration).close(
            self.manifest,
            user=self.operator,
            uf="MG",
            municipality_code="3106200",
            closing_date=date(2026, 11, 10),
            idempotency_key="encerramento-ja-registrado",
        )

        self.assertEqual(operation.estado, "HOMOLOGADO")
        self.assertEqual(operation.protocolo, "935260000000001")
        event_client.assert_not_called()
        self.manifest.refresh_from_db()
        self.assertEqual(self.manifest.situacao, "ENCERRADO")

    def test_mdfe_ja_encerrado_e_idempotente(self):
        self.manifest.situacao = "ENCERRADO"
        self.manifest.save(update_fields=("situacao",))
        operation = OperacaoEncerramento.objects.create(
            manifesto=self.manifest, solicitado_por=self.operator, idempotency_key="old",
            identificador_evento=f"ID110112{self.manifest.chave}01", uf="MG", municipio_codigo="3106200",
            municipio_nome="Belo Horizonte", data_encerramento=date(2026, 11, 10), estado="HOMOLOGADO",
            protocolo="935260000000001",
        )
        result = EncerramentoMdfeService(self.configuration).close(
            self.manifest, user=self.operator, uf="MG", municipality_code="3106200",
            closing_date=date(2026, 11, 10), idempotency_key="new",
        )
        self.assertEqual(result.id, operation.id)
        self.assertEqual(OperacaoEncerramento.objects.count(), 1)

    @patch("mdfe.services.encerramento_service.SefazClient")
    @patch("mdfe.services.encerramento_service.ConsultaMdfeService.document_status")
    def test_rejeicao_fiscal(self, status_mock, client_class):
        status_mock.return_value = DocumentStatus("100", "Autorizado", "935260000000000", "2026-11-01T10:00:00-03:00")
        client_class.return_value.send.return_value = self.sefaz_response(event_xml("580", "Rejeição fiscal", ""))
        operation = EncerramentoMdfeService(self.configuration).close(
            self.manifest, user=self.operator, uf="MG", municipality_code="3106200",
            closing_date=date(2026, 11, 10), idempotency_key="rejeicao",
        )
        self.assertEqual(operation.estado, "REJEITADO")
        self.manifest.refresh_from_db()
        self.assertNotEqual(self.manifest.situacao, "ENCERRADO")

    @patch("mdfe.services.encerramento_service.SefazClient")
    @patch("mdfe.services.encerramento_service.ConsultaMdfeService.document_status")
    def test_encerramento_homologado(self, status_mock, client_class):
        self.manifest.xml_criptografado = b"conteudo-criptografado"
        self.manifest.xml_status = Manifesto.XmlStatus.DISPONIVEL
        self.manifest.xml_sha256 = "a" * 64
        self.manifest.destinos = [{"codigo": "3106200", "municipio": "Belo Horizonte", "uf": "MG"}]
        self.manifest.save(update_fields=("xml_criptografado", "xml_status", "xml_sha256", "destinos"))
        status_mock.return_value = DocumentStatus("100", "Autorizado", "935260000000000", "2026-11-01T10:00:00-03:00")
        client_class.return_value.send.return_value = self.sefaz_response(event_xml())
        operation = EncerramentoMdfeService(self.configuration).close(
            self.manifest, user=self.operator, uf="MG", municipality_code="3106200",
            closing_date=date(2026, 11, 10), idempotency_key="sucesso",
        )
        self.assertEqual(operation.estado, "HOMOLOGADO")
        self.assertEqual(operation.protocolo, "935260000000001")
        self.manifest.refresh_from_db()
        self.assertEqual(self.manifest.situacao, "ENCERRADO")
        self.assertIsNone(self.manifest.xml_criptografado)
        self.assertEqual(self.manifest.xml_status, Manifesto.XmlStatus.REMOVIDO)
        self.assertEqual(self.manifest.snapshot_fiscal["chave"], self.manifest.chave)
        self.assertEqual(self.manifest.snapshot_fiscal["destinos"][0]["municipio"], "Belo Horizonte")

    @patch("mdfe.services.encerramento_service.SefazClient")
    @patch("mdfe.services.encerramento_service.ConsultaMdfeService.document_status")
    def test_timeout_apos_transmissao_fica_a_confirmar(self, status_mock, client_class):
        status_mock.return_value = DocumentStatus("100", "Autorizado", "935260000000000", "2026-11-01T10:00:00-03:00")
        client_class.return_value.send.side_effect = MdfeCommunicationError("Timeout", code="sefaz_timeout", inconclusive=True)
        operation = EncerramentoMdfeService(self.configuration).close(
            self.manifest, user=self.operator, uf="MG", municipality_code="3106200",
            closing_date=date(2026, 11, 10), idempotency_key="timeout",
        )
        self.assertEqual(operation.estado, "A_CONFIRMAR")
        self.manifest.refresh_from_db()
        self.assertEqual(self.manifest.situacao, "A_CONFIRMAR")

    @patch("mdfe.services.encerramento_service.SefazClient")
    @patch("mdfe.services.encerramento_service.ConsultaMdfeService.document_status")
    def test_tentativa_duplicada_nao_retransmite(self, status_mock, client_class):
        status_mock.return_value = DocumentStatus("100", "Autorizado", "935260000000000", "2026-11-01T10:00:00-03:00")
        client_class.return_value.send.return_value = self.sefaz_response(event_xml("580", "Rejeitado", ""))
        service = EncerramentoMdfeService(self.configuration)
        first = service.close(self.manifest, user=self.operator, uf="MG", municipality_code="3106200", closing_date=date(2026, 11, 10), idempotency_key="igual")
        second = service.close(self.manifest, user=self.operator, uf="MG", municipality_code="3106200", closing_date=date(2026, 11, 10), idempotency_key="igual")
        self.assertEqual(first.id, second.id)
        self.assertEqual(client_class.return_value.send.call_count, 1)

    def test_requisicoes_simultaneas_sao_bloqueadas(self):
        OperacaoEncerramento.objects.create(
            manifesto=self.manifest, solicitado_por=self.operator, idempotency_key="ativa",
            identificador_evento=f"ID110112{self.manifest.chave}01", uf="MG", municipio_codigo="3106200",
            municipio_nome="Belo Horizonte", data_encerramento=date(2026, 11, 10), estado="PROCESSANDO",
        )
        with self.assertRaises(MdfeError) as context:
            EncerramentoMdfeService(self.configuration).close(
                self.manifest, user=self.operator, uf="MG", municipality_code="3106200",
                closing_date=date(2026, 11, 10), idempotency_key="concorrente",
            )
        self.assertEqual(context.exception.code, "closing_in_progress")

    @patch("mdfe.views.EncerramentoMdfeService.close", side_effect=DatabaseError("storage failed"))
    def test_falha_de_armazenamento_nao_vaza_detalhes(self, _close):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            f"/api/mdfe/{self.manifest.chave}/encerrar/",
            {"uf": "MG", "municipio_codigo": "3106200", "data_encerramento": "2026-11-10", "confirmacao": True},
            format="json", HTTP_X_EMPRESA_ID=self.company.id,
        )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("storage failed", str(response.data))

    def test_controle_de_acesso_por_empresa_e_papel(self):
        self.client.force_authenticate(self.other)
        denied = self.client.get("/api/mdfe/pendentes/", HTTP_X_EMPRESA_ID=self.company.id)
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.reader)
        denied_close = self.client.post(
            f"/api/mdfe/{self.manifest.chave}/encerrar/",
            {"uf": "MG", "municipio_codigo": "3106200", "data_encerramento": "2026-11-10", "confirmacao": True},
            format="json", HTTP_X_EMPRESA_ID=self.company.id,
        )
        self.assertEqual(denied_close.status_code, 403)

    def test_endpoint_mdfe_lista_e_cria_empresa_inicial(self):
        self.client.force_authenticate(self.admin)
        listed = self.client.get("/api/mdfe/empresas/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["id"], self.company.id)
        self.assertEqual(listed.data[0]["papel"], "ADMIN")

        self.client.force_authenticate(self.other)
        created = self.client.post("/api/mdfe/empresas/", {}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["papel"], "ADMIN")
        self.assertTrue(MembroEmpresa.objects.filter(usuario=self.other, empresa_id=created.data["id"]).exists())

    def test_configuracao_nao_expoe_certificado_ou_senha(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/mdfe/configuracao/", HTTP_X_EMPRESA_ID=self.company.id)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("certificado_criptografado", body)
        self.assertNotIn("senha_criptografada", body)
        self.assertNotIn("senha", " ".join(body.keys()).lower())

    def test_admin_configura_certificado_a1(self):
        self.configuration.delete()
        pfx, _, _ = certificate_pfx()
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            "/api/mdfe/configuracao/",
            {
                "razao_social": "Transportadora Teste Ltda",
                "cnpj": CNPJ,
                "uf": "MG",
                "ambiente": "HOMOLOGACAO",
                "certificado": SimpleUploadedFile("certificado-teste.pfx", pfx, content_type="application/x-pkcs12"),
                "senha_certificado": "senha-forte",
            },
            format="multipart",
            HTTP_X_EMPRESA_ID=self.company.id,
        )
        self.assertEqual(response.status_code, 200, response.data)
        configuration = ConfiguracaoFiscal.objects.get(empresa=self.company)
        self.assertNotEqual(bytes(configuration.certificado_criptografado), pfx)
        self.assertNotIn("senha_certificado", response.data)

    @patch("mdfe.views.ConsultaMdfeService.refresh_non_closed")
    def test_perfil_leitura_pode_atualizar_consulta(self, refresh):
        audit = ConsultaManifestos.objects.create(
            empresa=self.company, solicitado_por=self.reader, estado="SUCESSO", codigo_sefaz="112",
            descricao_sefaz="Não existem MDF-e não encerrados", finalizada_em=timezone.now(),
        )
        refresh.return_value = audit
        self.client.force_authenticate(self.reader)
        response = self.client.post("/api/mdfe/atualizar/", HTTP_X_EMPRESA_ID=self.company.id)
        self.assertEqual(response.status_code, 200)

    def test_assinatura_xml_e_schema_oficiais(self):
        # Usa o material já validado do fixture, sem expor segredo no XML além do certificado público.
        from mdfe.services.certificate_service import load_configuration_material
        material = load_configuration_material(self.configuration)
        event, event_id = build_closing_event(
            self.configuration, self.manifest, uf="MG", municipality_code="3106200",
            closing_date=date(2026, 11, 10), event_time=datetime(2026, 11, 10, 10, tzinfo=dt_timezone(timedelta(hours=-3))),
            material=material,
        )
        info = event.xpath("//*[local-name()='infEvento']")[0]
        reference = event.xpath("//*[local-name()='Reference']")[0]
        self.assertEqual(reference.get("URI"), f"#{event_id}")
        digest = base64.b64decode(event.xpath("string(//*[local-name()='DigestValue'])"))
        canonical_info = etree.tostring(
            etree.fromstring(etree.tostring(info)), method="c14n", exclusive=False, with_comments=False
        )
        import hashlib
        self.assertEqual(digest, hashlib.sha1(canonical_info).digest())
        signed_info = event.xpath("//*[local-name()='SignedInfo']")[0]
        signature = base64.b64decode(event.xpath("string(//*[local-name()='SignatureValue'])"))
        material.certificate.public_key().verify(
            signature,
            etree.tostring(
                etree.fromstring(etree.tostring(signed_info)),
                method="c14n", exclusive=False, with_comments=False,
            ),
            padding.PKCS1v15(), hashes.SHA1(),
        )
        event_text = etree.tostring(event, encoding="unicode")
        self.assertNotIn("condutor", event_text)
        self.assertNotIn("infMunDescarga", event_text)
        self.assertEqual(event.xpath("string(//*[local-name()='evEncMDFe']/*[local-name()='cMun'])"), "3106200")

    def test_erro_de_schema_informa_arquivo_e_campo_invalido(self):
        from mdfe.services.certificate_service import load_configuration_material

        material = load_configuration_material(self.configuration)
        manifest = SimpleNamespace(
            chave=self.manifest.chave,
            cnpj_emitente=self.manifest.cnpj_emitente,
            protocolo_autorizacao="protocolo-invalido",
        )
        with self.assertRaises(MdfeError) as context:
            build_closing_event(
                self.configuration,
                manifest,
                uf="MG",
                municipality_code="3106200",
                closing_date=date(2026, 11, 10),
                event_time=datetime(2026, 11, 10, 10, tzinfo=dt_timezone(timedelta(hours=-3))),
                material=material,
            )

        self.assertEqual(context.exception.code, "invalid_mdfe_schema")
        self.assertIn("evEncMDFe_v3.00.xsd", context.exception.message)
        self.assertIn("nProt", context.exception.message)

    def test_encerramento_rejeita_campos_extraidos_do_xml(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            f"/api/mdfe/{self.manifest.chave}/encerrar/",
            {
                "uf": "MG",
                "municipio_codigo": "3106200",
                "data_encerramento": "2026-11-10",
                "confirmacao": True,
                "destinos": [{"codigo": "9999999"}],
                "condutores": [{"nome": "Não deve ser transmitido"}],
            },
            format="json",
            HTTP_X_EMPRESA_ID=self.company.id,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Campos não permitidos", str(response.data))
        self.assertFalse(OperacaoEncerramento.objects.exists())

    @patch("mdfe.services.xml_import_service.validate_schema")
    def test_importa_xml_e_vincula_motorista_pelo_cpf(self, _validate_schema):
        driver = Motorista.objects.create(
            usuario=self.admin,
            nome="João da Silva",
            cpf="529.982.247-25",
            idade=38,
            venc_cnh=date(2027, 12, 31),
        )
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        self.client.force_authenticate(self.operator)

        response = self.client.post(
            "/api/mdfe/importar-xml/",
            {"arquivos": SimpleUploadedFile("mdfe.xml", xml, content_type="application/xml")},
            format="multipart",
            HTTP_X_EMPRESA_ID=self.company.id,
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["importados"][0]["vinculados"], 1)
        conductor = ManifestoCondutor.objects.get(manifesto=self.manifest)
        self.assertEqual(conductor.motorista, driver)
        self.manifest.refresh_from_db()
        self.assertIsNotNone(self.manifest.data_emissao)
        self.assertEqual(len(self.manifest.xml_sha256), 64)
        self.assertEqual(self.manifest.xml_status, Manifesto.XmlStatus.DISPONIVEL)
        self.assertEqual(self.manifest.xml_classificacao, Manifesto.XmlClassificacao.VERIFICADO)
        self.assertTrue(self.manifest.xml_criptografado)
        self.assertEqual(self.manifest.destinos[0]["municipio"], "Belo Horizonte")

        listing = self.client.get("/api/mdfe/pendentes/", HTTP_X_EMPRESA_ID=self.company.id)
        serialized = listing.data["results"]["items"][0]["condutores"][0]
        self.assertEqual(serialized["nome"], "João da Silva")
        self.assertTrue(serialized["vinculado"])
        self.assertNotIn("52998224725", str(serialized))

    @patch("mdfe.services.xml_import_service.validate_schema")
    def test_importacao_rejeita_xml_alterado_apos_assinatura(self, _validate_schema):
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        tampered = xml.replace("João da Silva".encode(), "João de Souza".encode())
        self.client.force_authenticate(self.operator)

        response = self.client.post(
            "/api/mdfe/importar-xml/",
            {"arquivos": SimpleUploadedFile("alterado.xml", tampered, content_type="application/xml")},
            format="multipart",
            HTTP_X_EMPRESA_ID=self.company.id,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["erros"][0]["code"], "invalid_xml_digest")
        self.assertFalse(ManifestoCondutor.objects.exists())

    @patch("mdfe.services.xml_import_service.validate_schema")
    def test_importacao_mantem_condutor_nao_cadastrado(self, _validate_schema):
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        self.client.force_authenticate(self.operator)

        response = self.client.post(
            "/api/mdfe/importar-xml/",
            {"arquivos": SimpleUploadedFile("mdfe.xml", xml, content_type="application/xml")},
            format="multipart",
            HTTP_X_EMPRESA_ID=self.company.id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["importados"][0]["nao_vinculados"], 1)
        conductor = ManifestoCondutor.objects.get()
        self.assertIsNone(conductor.motorista)
        self.assertEqual(conductor.nome_xml, "João da Silva")

    @patch("mdfe.services.xml_import_service.validate_schema")
    def test_perfil_leitura_nao_pode_importar_xml(self, _validate_schema):
        xml = processed_mdfe_xml(access_key(), self.signing_key, self.signing_certificate)
        self.client.force_authenticate(self.reader)

        response = self.client.post(
            "/api/mdfe/importar-xml/",
            {"arquivos": SimpleUploadedFile("mdfe.xml", xml, content_type="application/xml")},
            format="multipart",
            HTTP_X_EMPRESA_ID=self.company.id,
        )

        self.assertEqual(response.status_code, 403)

