import hashlib
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from acertos.models import Acerto, ItemAcerto
from caminhoes.models import Caminhao
from inteligencia_logistica.models import Empresa, MembroEmpresa
from mdfe.models import ConfiguracaoFiscal, Manifesto
from mdfe.services.certificate_service import encrypt_secret
from mdfe.services.exceptions import MdfeCommunicationError
from motoristas.models import Motorista
from viagens.models import ImportacaoMdfeViagem, Viagem
from viagens.services.mdfe_viagem_service import extrair_dados_viagem_mdfe


FERNET_KEY = "K9rDFqrgloA_Y0_ZWzZRxfZW4Gy1VWxPGqQqozbEphg="
CNPJ = "12345678000195"


def fiscal_key(model, number, numeric_code=12345678):
    base = f"312611{CNPJ}{model}001{number:09d}1{numeric_code:08d}"
    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(base), [2, 3, 4, 5, 6, 7, 8, 9] * 6)
    )
    remainder = total % 11
    digit = 0 if remainder in (0, 1) else 11 - remainder
    return base + str(digit)


def mdfe_xml(
    mdfe_key,
    *,
    cte_keys=None,
    drivers=None,
    origins=None,
    destinations=None,
    quantity="10000.0000",
    unit="01",
    contracts=None,
    protocol="935260000000000",
):
    cte_keys = [fiscal_key("57", 266)] if cte_keys is None else cte_keys
    drivers = [("Motorista Sintético", "52998224725")] if drivers is None else drivers
    origins = [("3142809", "Monte Alegre de Minas")] if origins is None else origins
    destinations = [("3150604", "Piracema")] if destinations is None else destinations
    contracts = [{"value": "900.00", "components": [("01", "FRETE", "900.00")]}] if contracts is None else contracts

    origin_xml = "".join(
        f"<infMunCarrega><cMunCarrega>{code}</cMunCarrega><xMunCarrega>{name}</xMunCarrega></infMunCarrega>"
        for code, name in origins
    )
    driver_xml = "".join(
        f"<condutor><xNome>{name}</xNome><CPF>{cpf}</CPF></condutor>" for name, cpf in drivers
    )
    destination_xml = "".join(
        "<infMunDescarga>"
        f"<cMunDescarga>{code}</cMunDescarga><xMunDescarga>{name}</xMunDescarga>"
        + "".join(f"<infCTe><chCTe>{key}</chCTe></infCTe>" for key in cte_keys)
        + "</infMunDescarga>"
        for code, name in destinations
    )
    payment_xml = ""
    for contract in contracts:
        components = "".join(
            f"<Comp><tpComp>{kind}</tpComp><vComp>{value}</vComp><xComp>{description}</xComp></Comp>"
            for kind, description, value in contract.get("components", [])
        )
        payment_xml += f"<infPag><vContrato>{contract['value']}</vContrato>{components}<indPag>1</indPag></infPag>"

    mdfe_number = str(int(mdfe_key[25:34]))
    mdfe_series = str(int(mdfe_key[22:25]))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mdfeProc xmlns="http://www.portalfiscal.inf.br/mdfe" versao="3.00">
  <MDFe><infMDFe Id="MDFe{mdfe_key}" versao="3.00">
    <ide><cUF>31</cUF><tpAmb>2</tpAmb><serie>{mdfe_series}</serie><nMDF>{mdfe_number}</nMDF><dhEmi>2026-11-10T10:00:00-03:00</dhEmi><UFIni>MG</UFIni><UFFim>MG</UFFim>{origin_xml}</ide>
    <emit><CNPJ>{CNPJ}</CNPJ><xNome>Transportadora Sintética</xNome></emit>
    <infModal><rodo><veicTracao><placa>ABC1D23</placa>{driver_xml}</veicTracao><infANTT>{payment_xml}</infANTT></rodo></infModal>
    <infDoc>{destination_xml}</infDoc>
    <prodPred><tpCarga>05</tpCarga><xProd>PRODUTO SINTÉTICO</xProd></prodPred>
    <tot><qCTe>{len(cte_keys)}</qCTe><vCarga>30000.00</vCarga><cUnid>{unit}</cUnid><qCarga>{quantity}</qCarga></tot>
  </infMDFe></MDFe>
  <protMDFe versao="3.00"><infProt><tpAmb>2</tpAmb><chMDFe>{mdfe_key}</chMDFe><nProt>{protocol}</nProt><cStat>100</cStat><xMotivo>Autorizado</xMotivo></infProt></protMDFe>
</mdfeProc>'''.encode()


@override_settings(MDFE_ENCRYPTION_KEY=FERNET_KEY, MDFE_ENABLE_PRODUCTION=False)
class ImportacaoViagemMdfeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            "operador-viagem-mdfe",
            email="operador-viagem-mdfe@example.com",
            password="senha-forte",
        )
        self.other_user = User.objects.create_user(
            "outro-viagem-mdfe",
            email="outro-viagem-mdfe@example.com",
            password="senha-forte",
        )
        self.reader = User.objects.create_user(
            "leitor-viagem-mdfe",
            email="leitor-viagem-mdfe@example.com",
            password="senha-forte",
        )
        self.company = Empresa.objects.create(nome="Transportadora Sintética", slug="transportadora-sintetica")
        MembroEmpresa.objects.create(empresa=self.company, usuario=self.user, papel=MembroEmpresa.Papel.OPERADOR)
        MembroEmpresa.objects.create(empresa=self.company, usuario=self.reader, papel=MembroEmpresa.Papel.LEITURA)
        self.configuration = ConfiguracaoFiscal.objects.create(
            empresa=self.company,
            razao_social="Transportadora Sintética Ltda",
            cnpj=CNPJ,
            uf="MG",
            ambiente=ConfiguracaoFiscal.Ambiente.HOMOLOGACAO,
            certificado_criptografado=b"certificado-sintetico",
            senha_criptografada=b"senha-sintetica",
            certificado_nome="sintetico.pfx",
            certificado_fingerprint="0" * 64,
            certificado_cnpj=CNPJ,
            certificado_valido_de=timezone.now() - timedelta(days=1),
            certificado_valido_ate=timezone.now() + timedelta(days=30),
            atualizado_por=self.user,
        )
        truck = Caminhao.objects.create(usuario=self.user, nome_conjunto="Conjunto Sintético")
        self.driver = Motorista.objects.create(
            usuario=self.user,
            nome="Motorista Sintético",
            cpf="529.982.247-25",
            idade=35,
            venc_cnh="2030-01-01",
            caminhao=truck,
        )
        other_truck = Caminhao.objects.create(usuario=self.other_user, nome_conjunto="Outro Conjunto")
        self.other_driver = Motorista.objects.create(
            usuario=self.other_user,
            nome="Motorista de Outro Usuário",
            cpf="111.444.777-35",
            idade=40,
            venc_cnh="2030-01-01",
            caminhao=other_truck,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.headers = {"HTTP_X_EMPRESA_ID": self.company.id}

    def create_manifest(self, number=296, **xml_options):
        key = fiscal_key("58", number, numeric_code=12345000 + number)
        xml = mdfe_xml(key, **xml_options)
        manifest = Manifesto.objects.create(
            empresa=self.company,
            chave=key,
            numero=f"{number:09d}",
            cnpj_emitente=CNPJ,
            protocolo_autorizacao="935260000000000",
            situacao=Manifesto.Situacao.ABERTO,
            listado_ultima_consulta=True,
            data_emissao=timezone.now(),
            ultima_consulta_em=timezone.now(),
            xml_criptografado=encrypt_secret(xml),
            xml_sha256=hashlib.sha256(xml).hexdigest(),
            xml_status=Manifesto.XmlStatus.DISPONIVEL,
            xml_fonte=Manifesto.XmlFonte.PORTAL_NACIONAL,
            xml_classificacao=Manifesto.XmlClassificacao.INFORMATIVO,
            xml_assinatura_conteudo_validada=False,
        )
        return manifest

    def audit(self):
        return SimpleNamespace(
            id=1,
            estado="SUCESSO",
            quantidade=1,
            xml_baixados=0,
            xml_em_cache=1,
            xml_erros=0,
            finalizada_em=timezone.now(),
        )

    def consult(self):
        with patch("viagens.views.ConsultaMdfeService.refresh_non_closed", return_value=self.audit()):
            return self.client.post("/api/viagens/consultar-mdfe-abertos/", {}, format="json", **self.headers)

    def import_payload(self, manifest, **overrides):
        cte = fiscal_key("57", 266)
        data = {
            "mdfe_chave": manifest.chave,
            "motorista_id": self.driver.id,
            "data": "2026-11-10",
            "origem": "Monte Alegre de Minas",
            "destino": "Piracema",
            "cliente": "Cliente Sintético",
            "peso": "10.00",
            "valor_tonelada": "90.00",
            "teve_cte": True,
            "chave_cte": cte,
            "pago": False,
            "confirmar_divergencia_cpf": False,
            "confirmar_xml_informativo": True,
            "confirmar_possivel_duplicidade": False,
            "confirmar_diferenca_contrato": True,
        }
        data.update(overrides)
        return data

    def import_records(self, records):
        return self.client.post(
            "/api/viagens/importar-mdfe-confirmados/",
            {"registros": records},
            format="json",
            **self.headers,
        )

    def test_consulta_prepara_um_cte_sem_criar_viagem(self):
        manifest = self.create_manifest()

        response = self.consult()

        self.assertEqual(response.status_code, 200)
        item = response.data["manifestos"][0]
        self.assertEqual(item["chave_mdfe"], manifest.chave)
        self.assertEqual(item["ctes"][0]["numero"], "266")
        self.assertEqual(item["motorista_sugerido_id"], self.driver.id)
        self.assertEqual(item["peso_toneladas"], "10.00")
        self.assertEqual(item["valor_contrato"], "900.00")
        self.assertEqual(item["valor_tonelada_sugerido"], "90.00")
        self.assertTrue(item["xml_informativo"])
        self.assertFalse(item["assinatura_validada"])
        self.assertEqual(Viagem.objects.count(), 0)

    def test_extrai_multiplos_cte_sem_dividir_peso_ou_valores(self):
        manifest = self.create_manifest(
            cte_keys=[fiscal_key("57", 266), fiscal_key("57", 267, 87654321)]
        )

        response = self.consult()

        item = response.data["manifestos"][0]
        self.assertEqual(item["status"], "MULTIPLOS_CTE")
        self.assertEqual(len(item["ctes"]), 2)
        self.assertEqual(item["valor_tonelada_sugerido"], "")

    def test_extrai_manifesto_sem_cte_sem_inventar_numero(self):
        self.create_manifest(cte_keys=[])

        item = self.consult().data["manifestos"][0]

        self.assertEqual(item["ctes"], [])
        self.assertFalse(item["sugestao"]["teve_cte"])
        self.assertEqual(item["sugestao"]["chave_cte"], "")

    def test_converte_peso_por_unidade_e_exige_revisao_para_desconhecida(self):
        cases = [
            ("01", "36390.0000", Decimal("36.3900")),
            ("02", "36.3900", Decimal("36.3900")),
            ("99", "36.3900", None),
        ]
        for index, (unit, quantity, expected) in enumerate(cases, start=1):
            with self.subTest(unit=unit):
                manifest = self.create_manifest(number=300 + index, unit=unit, quantity=quantity)
                extracted = extrair_dados_viagem_mdfe(manifest, self.user)
                self.assertEqual(extracted["peso_toneladas"], expected)

    def test_valor_sugerido_so_existe_para_um_contrato_inequivoco(self):
        no_contract = self.create_manifest(number=310, contracts=[])
        multiple = self.create_manifest(
            number=311,
            contracts=[{"value": "500.00"}, {"value": "400.00"}],
        )
        components = self.create_manifest(
            number=312,
            contracts=[{"value": "900.00", "components": [("01", "FRETE", "800.00"), ("99", "OUTRO", "100.00")]}],
        )

        self.assertIsNone(extrair_dados_viagem_mdfe(no_contract, self.user)["valor_tonelada_sugerido"])
        self.assertIsNone(extrair_dados_viagem_mdfe(multiple, self.user)["valor_tonelada_sugerido"])
        extracted = extrair_dados_viagem_mdfe(components, self.user)
        self.assertEqual(extracted["valor_tonelada_sugerido"], Decimal("90.00"))
        self.assertEqual(len(extracted["contratos"][0]["componentes"]), 2)

    def test_multiplos_condutores_exigem_selecao_do_responsavel(self):
        self.create_manifest(drivers=[("Motorista Sintético", "52998224725"), ("Outro", "11144477735")])

        item = self.consult().data["manifestos"][0]

        self.assertEqual(len(item["condutores"]), 2)
        self.assertIsNone(item["motorista_sugerido_id"])
        self.assertNotIn("cpf", item["condutores"][0])

    def test_xml_indisponivel_e_erro_sefaz_sao_tratados(self):
        manifest = self.create_manifest()
        manifest.xml_criptografado = None
        manifest.xml_status = Manifesto.XmlStatus.ERRO
        manifest.xml_ultimo_erro = "XML não disponibilizado."
        manifest.save(update_fields=("xml_criptografado", "xml_status", "xml_ultimo_erro"))
        self.assertEqual(self.consult().data["manifestos"][0]["status"], "XML_INDISPONIVEL")

        with patch(
            "viagens.views.ConsultaMdfeService.refresh_non_closed",
            side_effect=MdfeCommunicationError("SEFAZ indisponível para teste."),
        ):
            response = self.client.post("/api/viagens/consultar-mdfe-abertos/", {}, format="json", **self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["detail"], "SEFAZ indisponível para teste.")

    def test_usuario_sem_acesso_a_empresa_nao_consulta(self):
        self.create_manifest()
        self.client.force_authenticate(self.other_user)

        response = self.client.post("/api/viagens/consultar-mdfe-abertos/", {}, format="json", **self.headers)

        self.assertEqual(response.status_code, 403)

    def test_perfil_leitura_pode_consultar_mas_nao_salvar(self):
        self.create_manifest()
        self.client.force_authenticate(self.reader)

        consult_response = self.consult()
        import_response = self.client.post(
            "/api/viagens/importar-mdfe-confirmados/",
            {"registros": []},
            format="json",
            **self.headers,
        )

        self.assertEqual(consult_response.status_code, 200)
        self.assertEqual(import_response.status_code, 403)

    def test_importacao_cria_viagem_normal_com_vinculo_atomico(self):
        manifest = self.create_manifest()

        response = self.import_records([self.import_payload(manifest)])

        self.assertEqual(response.status_code, 201, response.data)
        trip = Viagem.objects.get()
        link = ImportacaoMdfeViagem.objects.get()
        self.assertEqual(link.viagem, trip)
        self.assertEqual(trip.usuario, self.user)
        self.assertEqual(trip.motorista, self.driver)
        self.assertEqual(trip.numero_cte, "266")
        self.assertEqual(trip.calcular_valor_bruto(), Decimal("900.00"))
        self.assertEqual(trip.calcular_desconto_cte(), Decimal("90.00"))
        self.assertEqual(trip.valor_total, Decimal("810.00"))

        list_response = self.client.get("/api/viagens/?teve_cte=com_cte")
        self.assertEqual(list_response.status_code, 200)
        data = list_response.data if isinstance(list_response.data, list) else list_response.data["results"]
        self.assertEqual([item["id"] for item in data], [trip.id])

    def test_viagem_importada_participa_do_acerto_sem_adaptacao(self):
        manifest = self.create_manifest()
        self.assertEqual(self.import_records([self.import_payload(manifest)]).status_code, 201)
        trip = Viagem.objects.get()

        response = self.client.get(
            "/api/viagens/gerar_acerto/",
            {
                "motorista_id": self.driver.id,
                "inicio": "2026-11-10",
                "fim": "2026-11-10",
                "salvar": "true",
            },
        )

        self.assertEqual(response.status_code, 200)
        settlement = Acerto.objects.get()
        item = ItemAcerto.objects.get(acerto=settlement)
        self.assertEqual(item.viagem, trip)
        self.assertEqual(settlement.valor_total_viagens, trip.valor_total)
        self.assertEqual(settlement.desconto_cte, Decimal("90.00"))

    def test_nao_salva_sem_motorista_cadastrado_ou_com_motorista_alheio(self):
        manifest = self.create_manifest()
        missing = self.import_records([self.import_payload(manifest, motorista_id=999999)])
        self.assertEqual(missing.status_code, 400)
        self.assertIn("Motorista não encontrado no cadastro", missing.data["detail"])

        other = self.import_records([self.import_payload(manifest, motorista_id=self.other_driver.id)])
        self.assertEqual(other.status_code, 400)
        self.assertEqual(Viagem.objects.count(), 0)
        self.assertEqual(ImportacaoMdfeViagem.objects.count(), 0)

    def test_divergencia_de_cpf_e_xml_informativo_exigem_confirmacao(self):
        manifest = self.create_manifest(drivers=[("Condutor XML", "11144477735")], contracts=[])
        payload = self.import_payload(
            manifest,
            valor_tonelada="100.00",
            confirmar_xml_informativo=False,
            confirmar_diferenca_contrato=False,
        )
        response = self.import_records([payload])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "driver_cpf_mismatch_confirmation_required")

        payload["confirmar_divergencia_cpf"] = True
        response = self.import_records([payload])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "informational_xml_confirmation_required")

    def test_impede_duplicidade_de_mdfe_e_cte(self):
        first = self.create_manifest(number=320)
        payload = self.import_payload(first)
        self.assertEqual(self.import_records([payload]).status_code, 201)
        self.assertEqual(self.import_records([payload]).status_code, 409)

        second = self.create_manifest(number=321)
        response = self.import_records([self.import_payload(second)])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "cte_already_imported")
        self.assertEqual(Viagem.objects.count(), 1)

    def test_lote_e_atomico_quando_um_motorista_e_invalido(self):
        first = self.create_manifest(number=330, cte_keys=[fiscal_key("57", 330, 33333333)], contracts=[])
        second = self.create_manifest(number=331, cte_keys=[fiscal_key("57", 331, 44444444)], contracts=[])
        first_payload = self.import_payload(
            first,
            chave_cte=fiscal_key("57", 330, 33333333),
            valor_tonelada="100.00",
            confirmar_diferenca_contrato=False,
        )
        second_payload = self.import_payload(
            second,
            chave_cte=fiscal_key("57", 331, 44444444),
            motorista_id=self.other_driver.id,
            valor_tonelada="100.00",
            confirmar_diferenca_contrato=False,
        )

        response = self.import_records([first_payload, second_payload])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Viagem.objects.count(), 0)
        self.assertEqual(ImportacaoMdfeViagem.objects.count(), 0)

    def test_salva_multiplas_viagens_sem_cte_com_chave_fiscal_nula(self):
        first = self.create_manifest(number=340, cte_keys=[], contracts=[])
        second = self.create_manifest(number=341, cte_keys=[], contracts=[])
        records = [
            self.import_payload(
                manifest,
                teve_cte=False,
                chave_cte="",
                valor_tonelada="100.00",
                confirmar_diferenca_contrato=False,
            )
            for manifest in (first, second)
        ]

        response = self.import_records(records)

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Viagem.objects.count(), 2)
        self.assertEqual(ImportacaoMdfeViagem.objects.filter(chave_cte__isnull=True).count(), 2)

    def test_importacao_nao_altera_viagens_ou_acertos_existentes(self):
        existing = Viagem.objects.create(
            usuario=self.user,
            motorista=self.driver,
            data="2026-10-01",
            origem="Origem anterior",
            destino="Destino anterior",
            cliente="Cliente anterior",
            peso=Decimal("20.00"),
            valor_tonelada=Decimal("50.00"),
            teve_cte=False,
            pago=True,
        )
        manifest = self.create_manifest()

        self.assertEqual(self.import_records([self.import_payload(manifest)]).status_code, 201)

        existing.refresh_from_db()
        self.assertEqual(existing.valor_total, Decimal("1000.00"))
        self.assertTrue(existing.pago)
        self.assertEqual(Acerto.objects.count(), 0)

    def test_cadastro_manual_rejeita_motorista_de_outro_usuario(self):
        response = self.client.post(
            "/api/viagens/",
            {
                "motorista": self.other_driver.id,
                "data": "2026-11-10",
                "origem": "Origem",
                "destino": "Destino",
                "cliente": "Cliente",
                "peso": "10.00",
                "valor_tonelada": "100.00",
                "teve_cte": False,
                "pago": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Viagem.objects.count(), 0)
