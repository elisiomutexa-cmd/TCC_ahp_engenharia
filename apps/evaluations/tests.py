from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.ahp.services import EvaluationAHPService
from apps.criteria.models import Criterion
from apps.evaluations.models import Evaluation, EvaluationCriterion, EvaluationSupplier, PairwiseComparison
from apps.evaluations.forms import ProposalAttachmentForm
from apps.services.models import EngineeringService
from apps.suppliers.models import Supplier


class EvaluationPersistenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gestor", password="SenhaSegura123")
        self.service = EngineeringService.objects.create(name="HVAC teste", service_type="HVAC", requested_at=date.today())
        self.evaluation = Evaluation.objects.create(service=self.service, evaluator=self.user)
        self.suppliers = [
            EvaluationSupplier.objects.create(evaluation=self.evaluation, supplier=Supplier.objects.create(name=f"Fornecedor {n}", nuit=f"T{n}", email=f"f{n}@test.local", phone="000"), snapshot_name=f"Fornecedor {n}")
            for n in (1, 2)
        ]
        self.criteria = [
            EvaluationCriterion.objects.create(evaluation=self.evaluation, criterion=Criterion.objects.create(code=f"C{n}", name=f"Critério {n}"), snapshot_code=f"C{n}", snapshot_name=f"Critério {n}")
            for n in (1, 2)
        ]

    def test_complete_evaluation_persists_ranking_and_consistency(self):
        PairwiseComparison.objects.create(evaluation=self.evaluation, matrix_type="CRITERIA", left_criterion=self.criteria[0], right_criterion=self.criteria[1], preferred="LEFT", intensity=3, value=Decimal("3"))
        for criterion in self.criteria:
            PairwiseComparison.objects.create(evaluation=self.evaluation, matrix_type="ALTERNATIVES", parent_criterion=criterion, left_supplier=self.suppliers[0], right_supplier=self.suppliers[1], preferred="LEFT", intensity=3, value=Decimal("3"))
        result = EvaluationAHPService(self.evaluation).compute()
        self.assertTrue(result.all_consistent)
        self.assertEqual(self.evaluation.rankings.count(), 2)
        self.assertTrue(self.evaluation.rankings.get(position=1).is_recommended)

    def test_proposal_attachment_accepts_pdf(self):
        form = ProposalAttachmentForm(
            data={
                "evaluation_supplier": self.suppliers[0].pk,
                "description": "Proposta técnica",
            },
            files={
                "file": SimpleUploadedFile(
                    "proposta.pdf",
                    b"%PDF-1.4 demonstracao",
                    content_type="application/pdf",
                )
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
