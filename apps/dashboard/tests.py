from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.evaluations.models import Evaluation
from apps.services.models import EngineeringService


class DashboardLocalizationTests(TestCase):
    def test_status_chart_uses_portuguese_labels(self):
        user = get_user_model().objects.create_user(
            username="avaliador",
            password="SenhaSegura123",
        )
        service = EngineeringService.objects.create(
            name="Serviço de teste",
            service_type="HVAC",
            requested_at=date.today(),
        )
        Evaluation.objects.create(
            service=service,
            evaluator=user,
            status=Evaluation.Status.IN_PROGRESS,
        )
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Em avaliação")
