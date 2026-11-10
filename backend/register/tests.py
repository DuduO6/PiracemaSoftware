from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class UserCnpjTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="Dudu", email="dudu@example.com", password="senha-segura"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_existing_user_can_register_cnpj(self):
        response = self.client.patch("/auth/user/", {"cnpj": "11.222.333/0001-81"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.cnpj, "11222333000181")
        self.assertEqual(response.data["cnpj"], "11222333000181")

    def test_invalid_cnpj_is_rejected(self):
        response = self.client.patch("/auth/user/", {"cnpj": "11.111.111/1111-11"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("cnpj", response.data)

    def test_cnpj_cannot_be_shared_by_accounts(self):
        get_user_model().objects.create_user(
            username="outro", email="outro@example.com", password="senha-segura", cnpj="11222333000181"
        )

        response = self.client.patch("/auth/user/", {"cnpj": "11.222.333/0001-81"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("outra conta", str(response.data["cnpj"][0]))

    def test_cnpj_can_be_removed(self):
        self.user.cnpj = "11222333000181"
        self.user.save(update_fields=("cnpj",))

        response = self.client.patch("/auth/user/", {"cnpj": ""}, format="json")

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.cnpj)

    def test_current_password_is_required_to_change_username(self):
        response = self.client.patch("/auth/user/", {"username": "novo-dudu"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("senha_atual", response.data)

    def test_username_can_be_changed_with_current_password(self):
        response = self.client.patch(
            "/auth/user/", {"username": "novo-dudu", "senha_atual": "senha-segura"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "novo-dudu")

    def test_wrong_current_password_is_rejected(self):
        response = self.client.patch(
            "/auth/user/", {"username": "novo-dudu", "senha_atual": "senha-errada"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("incorreta", str(response.data["senha_atual"][0]))

    def test_password_can_be_changed_with_confirmation(self):
        response = self.client.patch(
            "/auth/user/",
            {
                "senha_atual": "senha-segura",
                "nova_senha": "Uma-Nova-Senha-Forte-2026!",
                "confirmar_nova_senha": "Uma-Nova-Senha-Forte-2026!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["senha_alterada"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Uma-Nova-Senha-Forte-2026!"))

    def test_new_password_confirmation_must_match(self):
        response = self.client.patch(
            "/auth/user/",
            {
                "senha_atual": "senha-segura",
                "nova_senha": "Uma-Nova-Senha-Forte-2026!",
                "confirmar_nova_senha": "Outra-Senha-Forte-2026!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("confirmar_nova_senha", response.data)
