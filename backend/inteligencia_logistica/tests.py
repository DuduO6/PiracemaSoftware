from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (ConfiguracaoLogisticaEmpresa, Empresa, MembroEmpresa,
                     OportunidadeFrete, ParceiroFrete, PerfilEstrategia,
                     PoloLogisticoNacional, PracaPedagio, ProdutoLogistico,
                     ResultadoAprendizadoLogistico, TarifaPedagio)
from fretes.services.toll_service import InternalTollProvider, TollService
from .services import recomendar
from .planner import planejar_reposicionamento
from motoristas.models import Motorista
from viagens.models import Viagem


class InteligenciaLogisticaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("operador", "op@example.com", "senha-forte")
        self.a = Empresa.objects.create(nome="Transportadora A", slug="a")
        self.b = Empresa.objects.create(nome="Transportadora B", slug="b")
        MembroEmpresa.objects.create(empresa=self.a, usuario=self.user, papel="ADMIN")
        MembroEmpresa.objects.create(empresa=self.b, usuario=self.user, papel="ADMIN")
        self.ca = ConfiguracaoLogisticaEmpresa.objects.create(empresa=self.a, km_vazio_maximo_desejado=100)
        ConfiguracaoLogisticaEmpresa.objects.create(empresa=self.b, km_vazio_maximo_desejado=10)
        self.pa = ParceiroFrete.objects.create(empresa=self.a, nome="Parceiro A", ativo=True)

    def oportunidade(self, empresa=None, **kwargs):
        dados = dict(empresa=empresa or self.a, origem="X", destino="Y", tipo_carga="GRAOS",
                     receita=10000, custo_estimado=3000, km_vazio=20,
                     probabilidade_continuidade=Decimal("0.5"), risco_retorno_vazio=Decimal("0.2"))
        dados.update(kwargs)
        return OportunidadeFrete.objects.create(**dados)

    def test_api_isola_empresas(self):
        oa, ob = self.oportunidade(), self.oportunidade(empresa=self.b)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get("/api/inteligencia-logistica/oportunidades/", HTTP_X_EMPRESA_ID=self.a.id)
        ids = {item["id"] for item in response.json()}
        self.assertIn(oa.id, ids)
        self.assertNotIn(ob.id, ids)

    def test_lista_somente_empresas_do_usuario(self):
        outro_usuario = get_user_model().objects.create_user("outro", "outro@example.com", "senha-forte")
        empresa_c = Empresa.objects.create(nome="Transportadora C", slug="c")
        MembroEmpresa.objects.create(empresa=empresa_c, usuario=outro_usuario)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get("/api/inteligencia-logistica/minhas-empresas/")
        ids = {item["id"] for item in response.json()}
        self.assertEqual(ids, {self.a.id, self.b.id})

    def test_cria_empresa_inicial_quando_usuario_nao_tem_tenant(self):
        usuario = get_user_model().objects.create_user("semempresa", "semempresa@example.com", "senha-forte")
        client = APIClient()
        client.force_authenticate(usuario)
        response = client.post("/api/inteligencia-logistica/minhas-empresas/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.json())
        self.assertTrue(MembroEmpresa.objects.filter(usuario=usuario, empresa_id=response.json()["id"], ativo=True).exists())
        self.assertTrue(ConfiguracaoLogisticaEmpresa.objects.filter(empresa_id=response.json()["id"], ativo=True).exists())

    def test_catalogo_nacional_e_somente_leitura(self):
        self.assertGreaterEqual(PoloLogisticoNacional.objects.count(), 50)
        self.assertEqual(ProdutoLogistico.objects.count(), 8)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get("/api/inteligencia-logistica/polos-nacionais/?categoria=POLO_SOJA&estado=MG")
        cidades = {item["cidade"] for item in response.json()}
        self.assertIn("Uberlândia", cidades)
        bloqueado = client.post("/api/inteligencia-logistica/polos-nacionais/", {"cidade": "Teste"}, format="json")
        self.assertEqual(bloqueado.status_code, 405)

    def test_rejeita_referencia_cruzada(self):
        parceiro_b = ParceiroFrete.objects.create(empresa=self.b, nome="B")
        client = APIClient()
        client.force_authenticate(self.user)
        payload = {"parceiro": parceiro_b.id, "origem": "X", "destino": "Y", "tipo_carga": "GRAOS", "receita": "1000.00"}
        response = client.post("/api/inteligencia-logistica/oportunidades/", payload, format="json", HTTP_X_EMPRESA_ID=self.a.id)
        self.assertEqual(response.status_code, 400)

    def test_sem_ia_e_incompatibilidade_antes_da_pontuacao(self):
        valida = self.oportunidade()
        invalida = self.oportunidade(receita=20000, km_vazio=150)
        resultado = recomendar(self.a, [valida, invalida])
        self.assertEqual(resultado["modo"], "REGRAS")
        self.assertEqual(resultado["recomendada"]["oportunidade_id"], valida.id)
        self.assertEqual(resultado["descartadas"][0]["id"], invalida.id)

    def test_calcula_valor_km_com_e_sem_deslocamento_vazio(self):
        oportunidade = self.oportunidade(
            receita=Decimal("1200"), custo_estimado=Decimal("200"), km_vazio=Decimal("20"),
            distancia_carregada_km=Decimal("100"),
        )
        resultado = recomendar(self.a, [oportunidade])["recomendada"]
        self.assertEqual(resultado["valor_km_carregado"], 12.0)
        self.assertEqual(resultado["valor_km_com_vazio"], 10.0)
        self.assertEqual(resultado["classificacao_km"], "RUIM")

    def test_perfil_personalizado_altera_pontuacao(self):
        perfil = PerfilEstrategia.objects.create(empresa=self.a, nome="Vazio", pesos={"lucro": 0, "km_vazio": 1, "tempo_espera": 0, "continuidade": 0, "risco": 0})
        perto = self.oportunidade(receita=5000, km_vazio=5)
        longe = self.oportunidade(receita=15000, km_vazio=90)
        resultado = recomendar(self.a, [perto, longe], perfil)
        self.assertEqual(resultado["recomendada"]["oportunidade_id"], perto.id)

    def test_endpoint_recomendacao_persiste_resultado_sem_ia(self):
        oportunidade = self.oportunidade(parceiro=self.pa)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            "/api/inteligencia-logistica/oportunidades/recomendar/",
            {"oportunidade_ids": [oportunidade.id]}, format="json", HTTP_X_EMPRESA_ID=self.a.id,
        )
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["modo"], "REGRAS")
        self.assertTrue(response.json()["recommendation_id"])
        decisao_id = response.json()["recommendation_id"]
        feedback = client.post(f"/api/inteligencia-logistica/decisoes/{decisao_id}/feedback/", {
            "aceitou_sugestao": True, "avaliacao": "RESULTADO_REGISTRADO",
            "resultado_real": {"receita": 10000, "custos_totais": 3500, "lucro_liquido": 6500,
                               "km_vazio": 18, "tempo_espera_horas": 3, "retorno_vazio": False},
        }, format="json", HTTP_X_EMPRESA_ID=self.a.id)
        self.assertEqual(feedback.status_code, 200, feedback.json())
        aprendizado = ResultadoAprendizadoLogistico.objects.get(decisao_id=decisao_id)
        self.assertEqual(aprendizado.lucro_real, Decimal("6500"))
        self.assertTrue(aprendizado.aceitou_sugestao)

    @patch("inteligencia_logistica.views.TollService")
    @patch("inteligencia_logistica.views.RoutingService")
    @patch("inteligencia_logistica.views.GeocodingService")
    def test_calculadora_frete_calcula_valores_sem_erro_decimal(self, geocoder_cls, routing_cls, toll_cls):
        geocoder_cls.return_value.geocode.side_effect = [
            {"cidade": "Uberlândia", "estado": "MG", "coordenadas": {"lat": -18.9, "lng": -48.2}},
            {"cidade": "Divinópolis", "estado": "MG", "coordenadas": {"lat": -20.1, "lng": -44.9}},
        ]
        routing_cls.return_value.calculate_route.return_value = {
            "distancia_km": 500, "duracao_formatada": "7h", "provedor": "fake", "rodovias_referencia": [],
        }
        toll_cls.return_value.estimate_tolls.return_value = {
            "total": 150, "itens": [{"nome": "Praça teste", "valor": 150}],
            "disponivel": True, "provedor": "interno", "mensagem": "",
        }
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post("/api/inteligencia-logistica/calcular-frete/", {
            "origem": "Uberlândia", "estado_origem": "MG", "destino": "Divinópolis",
            "estado_destino": "MG", "valor_frete": "5000.00", "eixos": 6,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["valor_km_bruto"], 10)
        self.assertEqual(response.json()["valor_pedagios"], 150)
        self.assertEqual(response.json()["valor_km_apos_pedagios"], 9.7)

    def test_provider_interno_detecta_praca_e_tarifa_por_eixo(self):
        praca = PracaPedagio.objects.create(
            rodovia="BR-000", praca="Praça teste", concessionaria="Concessionária",
            latitude=Decimal("-20.0005"), longitude=Decimal("-44.0000"), cidade="Teste",
            estado="MG", vigencia_inicio="2026-01-01", fonte="Fonte pública",
        )
        TarifaPedagio.objects.create(
            pedagio=praca, quantidade_eixos=6, valor=Decimal("42.50"),
            vigencia="2026-01-01", fonte="Fonte pública",
        )
        rota = {"geometria_preview": [{"lat": -20.0, "lng": -44.01}, {"lat": -20.0, "lng": -43.99}]}
        resultado = TollService(InternalTollProvider(tolerance_meters=200)).estimate_tolls(
            {}, {}, rota, {"quantidade_eixos": 6}
        )
        self.assertTrue(resultado["disponivel"])
        self.assertEqual(resultado["quantidade"], 1)
        self.assertEqual(resultado["total"], 42.5)

    def test_planejador_usa_apenas_historico_do_usuario_e_limita_raio(self):
        motorista = Motorista.objects.create(
            usuario=self.user, nome="Teste", cpf="999.999.999-01", idade=40, venc_cnh="2030-12-31"
        )
        for dia in (1, 2):
            Viagem.objects.create(
                usuario=self.user, motorista=motorista, data=f"2026-07-0{dia}", origem="Uberlândia",
                destino="Piracema", cliente="Cliente histórico", peso=Decimal("40"), valor_tonelada=Decimal("180"),
            )

        class GeocoderFake:
            pontos = {"Uberlândia": (0, 0), "Piracema": (0, 1), "Divinópolis": (0, 2)}
            def geocode(self, city, state="", target=""):
                lat, lng = self.pontos[city]
                return {"cidade": city, "estado": state, "coordenadas": {"lat": lat, "lng": lng}, "provedor": "fake"}

        class RouterFake:
            def calculate_route(self, origin, destination, payload):
                distancia = abs(origin["coordenadas"]["lng"] - destination["coordenadas"]["lng"]) * 100
                return {"distancia_km": distancia, "geometria_preview": [origin["coordenadas"], destination["coordenadas"]]}

        oportunidade = self.oportunidade(
            origem="Uberlândia/MG", receita=Decimal("1500"), distancia_carregada_km=Decimal("100"), km_vazio=Decimal("99")
        )

        resultado = planejar_reposicionamento(
            usuario=self.user, empresa=self.a, cidade_atual="Uberlândia", destino_pessoal="Divinópolis", raio_km=150,
            geocoder=GeocoderFake(), router=RouterFake(),
        )
        self.assertEqual(resultado["total_viagens_analisadas"], 2)
        self.assertEqual(resultado["sugestoes"][0]["km_vazio_ate_carregamento"], 0)
        self.assertEqual(resultado["sugestoes"][0]["confianca"], "MEDIA")
        self.assertEqual(len(resultado["fretes_historicos"]), 2)
        self.assertEqual(resultado["fretes_historicos"][0]["cliente"], "Cliente histórico")
        self.assertEqual(resultado["fretes_historicos"][0]["km_carregado_estimado"], 100)
        carga = resultado["oportunidades_adequadas"][0]
        self.assertEqual(carga["oportunidade_id"], oportunidade.id)
        self.assertEqual(carga["km_vazio_calculado"], 0)
        self.assertEqual(carga["valor_km_com_vazio"], 15)
        self.assertEqual(carga["classificacao"], "BOM")
