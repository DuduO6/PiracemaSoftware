from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Motorista


class MotoristaCpfValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="motorista-cpf",
            email="motorista-cpf@example.com",
            password="secret123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.payload = {
            "nome": "Motorista Válido",
            "cpf": "52998224725",
            "idade": 35,
            "venc_cnh": "2030-01-01",
            "caminhao": None,
        }

    def test_cadastra_e_formata_cpf_valido(self):
        response = self.client.post("/api/motoristas/", self.payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["cpf"], "529.982.247-25")

    def test_rejeita_cpf_invalido(self):
        payload = {**self.payload, "cpf": "111.111.111-11"}

        response = self.client.post("/api/motoristas/", payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(str(response.data["cpf"][0]), "Informe um CPF válido.")
        self.assertFalse(Motorista.objects.exists())

    def test_rejeita_mesmo_cpf_em_formatacao_diferente(self):
        Motorista.objects.create(usuario=self.user, **self.payload)
        payload = {**self.payload, "nome": "Outro Motorista", "cpf": "529.982.247-25"}

        response = self.client.post("/api/motoristas/", payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(str(response.data["cpf"][0]), "CPF já cadastrado.")
