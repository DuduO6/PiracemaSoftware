from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from caminhoes.models import Caminhao
from motoristas.models import Motorista

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
