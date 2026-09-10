from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def test_login_authenticates_user(self):
        get_user_model().objects.create_user(username="avaliador", password="SenhaSegura123")
        response = self.client.post(reverse("accounts:login"), {"username": "avaliador", "password": "SenhaSegura123"})
        self.assertRedirects(response, reverse("dashboard:home"))
