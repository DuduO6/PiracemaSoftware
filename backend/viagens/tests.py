from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from caminhoes.models import Caminhao
from motoristas.models import Motorista
from .models import Viagem

from .serializers import ViagemSerializer


class ViagemSerializerTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="secret123",
        )
        self.caminhao = Caminhao.objects.create(usuario=self.user, nome_conjunto="Conjunto Teste")
        self.motorista = Motorista.objects.create(
            usuario=self.user,
            nome="Motorista Teste",
            cpf="123.456.789-00",
            idade=30,
            venc_cnh="2030-01-01",
            caminhao=self.caminhao,
        )

    def test_aceita_valor_total_e_calcula_valor_tonelada(self):
        serializer = ViagemSerializer(data={
            "motorista": self.motorista.id,
            "data": "2026-03-27",
            "origem": "Arcos",
            "destino": "Piracema",
            "cliente": "Cliente Teste",
            "peso": "40.00",
            "valor_total_informado": "2000.00",
            "pago": False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        viagem = serializer.save(usuario=self.user)

        self.assertEqual(viagem.valor_tonelada, Decimal("50.00"))
        self.assertEqual(viagem.valor_total, Decimal("2000.00"))

    def test_aceita_valor_tonelada_e_mantem_calculo_normal(self):
        serializer = ViagemSerializer(data={
            "motorista": self.motorista.id,
            "data": "2026-03-27",
            "origem": "Arcos",
            "destino": "Piracema",
            "cliente": "Cliente Teste",
            "peso": "40.00",
            "valor_tonelada": "55.00",
            "pago": False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        viagem = serializer.save(usuario=self.user)

        self.assertEqual(viagem.valor_tonelada, Decimal("55.00"))
        self.assertEqual(viagem.valor_total, Decimal("2200.00"))

    def test_desconta_dez_por_cento_quando_tem_cte(self):
        serializer = ViagemSerializer(data={
            "motorista": self.motorista.id,
            "data": "2026-03-27",
            "origem": "Arcos",
            "destino": "Piracema",
            "cliente": "Cliente Teste",
            "peso": "40.00",
            "valor_tonelada": "55.00",
            "teve_cte": True,
            "numero_cte": "266",
            "pago": False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        viagem = serializer.save(usuario=self.user)

        self.assertEqual(viagem.valor_tonelada, Decimal("55.00"))
        self.assertEqual(viagem.valor_total, Decimal("1980.00"))

    def test_exige_numero_cte_quando_teve_cte(self):
        serializer = ViagemSerializer(data={
            "motorista": self.motorista.id,
            "data": "2026-03-27",
            "origem": "Arcos",
            "destino": "Piracema",
            "cliente": "Cliente Teste",
            "peso": "40.00",
            "valor_tonelada": "55.00",
            "teve_cte": True,
            "numero_cte": "",
            "pago": False,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("numero_cte", serializer.errors)

    def test_identifica_viagem_duplicada_com_mesmos_dados_principais(self):
        Viagem.objects.create(
            usuario=self.user,
            motorista=self.motorista,
            data="2026-03-27",
            origem="Arcos",
            destino="Piracema",
            cliente="Cliente Teste",
            peso=Decimal("40.00"),
            valor_tonelada=Decimal("55.00"),
            teve_cte=True,
            numero_cte="266",
            pago=False,
        )

        serializer = ViagemSerializer(
            data={
                "motorista": self.motorista.id,
                "data": "2026-03-27",
                "origem": " arcos ",
                "destino": "PIRACEMA",
                "cliente": "cliente teste",
                "peso": "40.00",
                "valor_tonelada": "55.00",
                "teve_cte": True,
                "numero_cte": "266",
                "pago": False,
            },
            context={"request": type("Request", (), {"user": self.user})()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        warning = serializer.build_duplicate_warning(serializer.validated_data)
        self.assertIsNotNone(warning)
        self.assertTrue(warning["duplicada"])

    def test_nao_marca_duplicidade_quando_valor_total_for_diferente(self):
        Viagem.objects.create(
            usuario=self.user,
            motorista=self.motorista,
            data="2026-03-27",
            origem="Arcos",
            destino="Piracema",
            cliente="Cliente Teste",
            peso=Decimal("40.00"),
            valor_tonelada=Decimal("55.00"),
            teve_cte=True,
            numero_cte="266",
            pago=False,
        )

        serializer = ViagemSerializer(
            data={
                "motorista": self.motorista.id,
                "data": "2026-03-27",
                "origem": "Arcos",
                "destino": "Piracema",
                "cliente": "Cliente Teste",
                "peso": "40.00",
                "valor_tonelada": "56.00",
                "teve_cte": True,
                "numero_cte": "266",
                "pago": False,
            },
            context={"request": type("Request", (), {"user": self.user})()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.build_duplicate_warning(serializer.validated_data))

    def test_permite_editar_a_mesma_viagem_sem_acusar_duplicidade(self):
        viagem = Viagem.objects.create(
            usuario=self.user,
            motorista=self.motorista,
            data="2026-03-27",
            origem="Arcos",
            destino="Piracema",
            cliente="Cliente Teste",
            peso=Decimal("40.00"),
            valor_tonelada=Decimal("55.00"),
            teve_cte=True,
            numero_cte="266",
            pago=False,
        )

        serializer = ViagemSerializer(
            instance=viagem,
            data={
                "motorista": self.motorista.id,
                "data": "2026-03-27",
                "origem": "Arcos",
                "destino": "Piracema",
                "cliente": "Cliente Teste",
                "peso": "40.00",
                "valor_tonelada": "55.00",
                "teve_cte": True,
                "numero_cte": "266",
                "pago": True,
            },
            context={"request": type("Request", (), {"user": self.user})()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.build_duplicate_warning(serializer.validated_data))


class ImportarCteTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="importador",
            email="importador@example.com",
            password="secret123",
        )
        self.caminhao = Caminhao.objects.create(usuario=self.user, nome_conjunto="Conjunto Importacao")
        self.motorista = Motorista.objects.create(
            usuario=self.user,
            nome="ROGERIO FERREIRA RIBEIRO",
            cpf="109.907.866-09",
            idade=40,
            venc_cnh="2030-01-01",
            caminhao=self.caminhao,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_importa_cte_e_preenche_campos_principais(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00">
  <CTe>
    <infCte versao="4.00" Id="teste">
      <ide>
        <nCT>266</nCT>
        <dhEmi>2026-04-10T09:23:16-03:00</dhEmi>
        <xMunIni>Entre Rios de Minas</xMunIni>
        <xMunFim>Itaguara</xMunFim>
        <toma3>
          <toma>3</toma>
        </toma3>
      </ide>
      <compl>
        <ObsCont xCampo="CPFMOTORISTA">
          <xTexto>109.907.866-09</xTexto>
        </ObsCont>
        <ObsCont xCampo="Mot">
          <xTexto>ROGERIO FERREIRA RIBEIRO-CH:05877412640-Lib:</xTexto>
        </ObsCont>
      </compl>
      <dest>
        <xNome>COOPERATIVA AGRO PECUARIA DE ITAGUARA LTDA</xNome>
        <enderDest>
          <xMun>ITAGUARA</xMun>
        </enderDest>
      </dest>
      <vPrest>
        <vTPrest>4107.36</vTPrest>
        <Comp>
          <xNome>Frete Peso</xNome>
          <vComp>4107.36</vComp>
        </Comp>
      </vPrest>
      <infCTeNorm>
        <infCarga>
          <infQ>
            <cUnid>01</cUnid>
            <tpMed>PESO</tpMed>
            <qCarga>0.0000</qCarga>
          </infQ>
          <infQ>
            <cUnid>03</cUnid>
            <tpMed>QUANTIDADE</tpMed>
            <qCarga>37000.0000</qCarga>
          </infQ>
        </infCarga>
      </infCTeNorm>
    </infCte>
  </CTe>
</cteProc>
"""
        arquivo = SimpleUploadedFile("cte.xml", xml.encode("utf-8"), content_type="text/xml")

        response = self.client.post("/api/viagens/importar_cte/", {"arquivo": arquivo}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["motorista"], self.motorista.id)
        self.assertEqual(response.data["numero_cte"], "266")
        self.assertEqual(response.data["origem"], "Entre Rios de Minas")
        self.assertEqual(response.data["destino"], "Itaguara")
        self.assertEqual(response.data["cliente"], "COOPERATIVA AGRO PECUARIA DE ITAGUARA LTDA")
        self.assertEqual(response.data["peso"], "37.00")
        self.assertEqual(response.data["valor_total_informado"], "4107.36")
        self.assertEqual(response.data["valor_tonelada"], "111.01")
        self.assertEqual(response.data["data"], "2026-04-10")
        self.assertTrue(response.data["teve_cte"])

    def test_verifica_duplicidade_por_endpoint(self):
        viagem = Viagem.objects.create(
            usuario=self.user,
            motorista=self.motorista,
            data="2026-04-10",
            origem="Entre Rios de Minas",
            destino="Itaguara",
            cliente="COOPERATIVA AGRO PECUARIA DE ITAGUARA LTDA",
            peso=Decimal("37.00"),
            valor_tonelada=Decimal("111.01"),
            teve_cte=True,
            numero_cte="266",
            pago=False,
        )

        response = self.client.post(
            "/api/viagens/verificar_duplicidade/",
            {
                "motorista": self.motorista.id,
                "data": "2026-04-10",
                "origem": "Entre Rios de Minas",
                "destino": "Itaguara",
                "cliente": "COOPERATIVA AGRO PECUARIA DE ITAGUARA LTDA",
                "peso": "37.00",
                "valor_tonelada": "111.01",
                "teve_cte": True,
                "numero_cte": "266",
                "pago": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["duplicada"])
        self.assertEqual(response.data["viagem_id"], viagem.id)

    def test_exporta_planilha_com_filtro_de_motorista_e_cte(self):
        outro_motorista = Motorista.objects.create(
            usuario=self.user,
            nome="Outro Motorista",
            cpf="321.654.987-00",
            idade=35,
            venc_cnh="2031-01-01",
            caminhao=self.caminhao,
        )

        Viagem.objects.create(
            usuario=self.user,
            motorista=self.motorista,
            data="2026-04-10",
            origem="Entre Rios de Minas",
            destino="Itaguara",
            cliente="Cliente Exportado",
            peso=Decimal("37.00"),
            valor_tonelada=Decimal("111.01"),
            teve_cte=True,
            numero_cte="266",
            pago=False,
        )
        Viagem.objects.create(
            usuario=self.user,
            motorista=outro_motorista,
            data="2026-04-11",
            origem="Oliveira",
            destino="Claudio",
            cliente="Cliente Fora",
            peso=Decimal("20.00"),
            valor_tonelada=Decimal("90.00"),
            teve_cte=False,
            numero_cte="",
            pago=True,
        )

        response = self.client.get(
            f"/api/viagens/exportar_planilha/?motorista={self.motorista.id}&teve_cte=com_cte"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("viagens_filtradas.csv", response["Content-Disposition"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("Cliente Exportado", content)
        self.assertNotIn("Cliente Fora", content)
