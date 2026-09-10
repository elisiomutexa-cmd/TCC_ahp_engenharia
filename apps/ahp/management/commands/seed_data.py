"""Cria dados fictícios reproduzíveis para demonstrar o fluxo completo AHP."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.ahp.services import EvaluationAHPService
from apps.criteria.models import Criterion
from apps.evaluations.models import Evaluation, EvaluationCriterion, EvaluationSupplier, PairwiseComparison
from apps.services.models import EngineeringService
from apps.suppliers.models import Supplier


class Command(BaseCommand):
    help = "Cria dados DEMONSTRAÇÃO fictícios, incluindo uma avaliação AHP calculada."

    def handle(self, *args, **options):
        user_model = get_user_model()
        admin, created = user_model.objects.get_or_create(
            username="admin", defaults={"email": "admin@demonstracao.local", "role": "ADMIN", "is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password("Admin@12345")
            admin.save()
        elif admin.role != "ADMIN":
            # Não altera a palavra-passe de uma conta existente.
            admin.role = "ADMIN"
            admin.save(update_fields=["role"])

        service, _ = EngineeringService.objects.get_or_create(
            name="DEMONSTRAÇÃO — Manutenção Corretiva de Sistema de Ar Condicionado",
            defaults={"service_type": "HVAC", "description": "Dados exclusivamente fictícios para validação do artefacto.", "location": "Maputo", "priority": "HIGH", "requested_at": date.today(), "deadline": date.today() + timedelta(days=14), "status": "OPEN", "is_demo": True},
        )
        supplier_names = ["Engenharia Técnica A", "Engenharia Técnica B", "Engenharia Técnica C", "Engenharia Técnica D"]
        suppliers = []
        for index, name in enumerate(supplier_names, 1):
            obj, _ = Supplier.objects.get_or_create(
                nuit=f"DEMO{index:05d}",
                defaults={"name": name, "email": f"fornecedor{index}@demonstracao.local", "phone": "+258 840000000", "city": "Maputo", "province": "Maputo", "specialties": "Manutenção HVAC (demonstração)", "experience_years": index + 4, "certifications": "Dados fictícios", "is_demo": True},
            )
            suppliers.append(obj)

        catalog = [
            ("C1", "Capacidade Técnica", ["Qualificação da equipa técnica", "Certificações", "Equipamentos e ferramentas disponíveis", "Capacidade de execução"]),
            ("C2", "Experiência", ["Anos de experiência", "Número de serviços semelhantes realizados", "Experiência no setor", "Referências de clientes"]),
            ("C3", "Custo", ["Preço da proposta", "Relação custo-benefício", "Condições de pagamento"]),
            ("C4", "Prazo/Tempo de Resposta", ["Tempo para iniciar o serviço", "Tempo estimado de execução", "Disponibilidade para emergências"]),
            ("C5", "Garantia", ["Período de garantia", "Cobertura da garantia", "Condições de assistência após o serviço"]),
            ("C6", "Suporte/Assistência Técnica", ["Disponibilidade de suporte", "Tempo de atendimento", "Atendimento pós-serviço", "Disponibilidade para manutenção corretiva"]),
        ]
        roots = []
        for order, (code, name, children) in enumerate(catalog, 1):
            root, _ = Criterion.objects.get_or_create(code=code, parent=None, defaults={"name": name, "sort_order": order})
            roots.append(root)
            for child_order, child in enumerate(children, 1):
                Criterion.objects.get_or_create(code=f"{code}.{child_order}", parent=root, defaults={"name": child, "sort_order": child_order})

        evaluation, created = Evaluation.objects.get_or_create(service=service, evaluator=admin, is_demo=True, defaults={"status": "IN_PROGRESS", "current_step": 5})
        if not created:
            self.stdout.write(self.style.WARNING("Dados de demonstração já existem; nada foi duplicado."))
            return
        eval_suppliers = [EvaluationSupplier.objects.create(evaluation=evaluation, supplier=s, snapshot_name=s.name) for s in suppliers]
        eval_criteria = [EvaluationCriterion.objects.create(evaluation=evaluation, criterion=c, snapshot_code=c.code, snapshot_name=c.name) for c in roots]
        # Vetores proporcionais criam matrizes perfeitamente consistentes (valores 1, 3 e 9 da escala Saaty).
        criterion_scale = [Decimal("9"), Decimal("9"), Decimal("3"), Decimal("3"), Decimal("1"), Decimal("1")]
        supplier_scale = [Decimal("9"), Decimal("3"), Decimal("1"), Decimal("1")]
        self._create_pairs(evaluation, "CRITERIA", eval_criteria, criterion_scale, "criterion")
        for leaf in eval_criteria:
            self._create_pairs(evaluation, "ALTERNATIVES", eval_suppliers, supplier_scale, "supplier", leaf)
        EvaluationAHPService(evaluation).compute()
        message = "Dados de demonstração criados."
        if created:
            message += " Login inicial: admin / Admin@12345 (altere a palavra-passe)."
        else:
            message += " A conta admin existente foi preservada; use a palavra-passe já definida."
        self.stdout.write(self.style.SUCCESS(message))

    def _create_pairs(self, evaluation, matrix_type, objects, scale, kind, parent=None):
        for i, left in enumerate(objects):
            for j, right in enumerate(objects[i + 1 :], i + 1):
                value = scale[i] / scale[j]
                preferred = "EQUAL" if value == 1 else "LEFT"
                intensity = int(value) if value >= 1 else int(1 / value)
                kwargs = {"evaluation": evaluation, "matrix_type": matrix_type, "parent_criterion": parent, "preferred": preferred, "intensity": intensity, "value": value}
                if kind == "criterion":
                    kwargs.update(left_criterion=left, right_criterion=right)
                else:
                    kwargs.update(left_supplier=left, right_supplier=right)
                PairwiseComparison.objects.create(**kwargs)
