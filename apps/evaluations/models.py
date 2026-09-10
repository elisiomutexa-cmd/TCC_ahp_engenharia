"""Avaliações AHP, comparações, pesos, prioridades, ranking e resultados."""

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.criteria.models import Criterion
from apps.services.models import EngineeringService
from apps.suppliers.models import Supplier


class Evaluation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        IN_PROGRESS = "IN_PROGRESS", "Em avaliação"
        INCONSISTENT = "INCONSISTENT", "Inconsistente"
        COMPLETED = "COMPLETED", "Concluída"
        CANCELLED = "CANCELLED", "Cancelada"

    service = models.ForeignKey(
        EngineeringService,
        on_delete=models.PROTECT,
        related_name="evaluations",
        verbose_name="Serviço",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluations",
        verbose_name="Avaliador",
    )
    objective = models.CharField(
        "Objetivo",
        max_length=255,
        default="Selecionar o melhor fornecedor para o serviço de engenharia",
    )
    notes = models.TextField("Observações", blank=True)
    status = models.CharField(
        "Estado",
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    current_step = models.PositiveSmallIntegerField("Passo do assistente", default=1)
    allow_inconsistent_completion = models.BooleanField(
        "Permitir conclusão com inconsistência",
        default=False,
        help_text="Apenas administrador pode ativar.",
    )
    completed_at = models.DateTimeField("Concluída em", null=True, blank=True)
    is_demo = models.BooleanField("Dados de demonstração", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["evaluator", "status"]),
        ]

    def __str__(self) -> str:
        return f"Avaliação #{self.pk} — {self.service}"

    @property
    def is_locked(self) -> bool:
        return self.status in {self.Status.COMPLETED, self.Status.CANCELLED}

    @property
    def is_editable(self) -> bool:
        return self.status in {
            self.Status.DRAFT,
            self.Status.IN_PROGRESS,
            self.Status.INCONSISTENT,
        }


class EvaluationSupplier(models.Model):
    """Snapshot do fornecedor na avaliação (histórico imutável após conclusão)."""

    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="evaluation_suppliers",
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    snapshot_name = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fornecedor da avaliação"
        unique_together = ("evaluation", "supplier")
        ordering = ["snapshot_name"]

    def __str__(self) -> str:
        return self.snapshot_name

    @property
    def label(self) -> str:
        return self.snapshot_name


class ProposalAttachment(models.Model):
    """Proposta ou documento submetido por um fornecedor para uma avaliação."""

    evaluation_supplier = models.ForeignKey(
        EvaluationSupplier,
        on_delete=models.CASCADE,
        related_name="proposal_attachments",
        verbose_name="Fornecedor da avaliação",
    )
    file = models.FileField(
        "Ficheiro",
        upload_to="proposals/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg"]
            )
        ],
    )
    description = models.CharField("Descrição", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_proposals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Anexo de proposta"
        verbose_name_plural = "Anexos de propostas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.description or self.file.name


class EvaluationCriterion(models.Model):
    """Critério/subcritério selecionado, com snapshot para rastreabilidade."""

    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="evaluation_criteria",
    )
    criterion = models.ForeignKey(Criterion, on_delete=models.PROTECT)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    snapshot_code = models.CharField(max_length=20)
    snapshot_name = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Critério da avaliação"
        unique_together = ("evaluation", "criterion")
        ordering = ["snapshot_code"]

    def __str__(self) -> str:
        return f"{self.snapshot_code} — {self.snapshot_name}"

    @property
    def label(self) -> str:
        return self.snapshot_name

    @property
    def is_leaf(self) -> bool:
        return not self.children.exists()


class PairwiseComparison(models.Model):
    class MatrixType(models.TextChoices):
        CRITERIA = "CRITERIA", "Critérios"
        SUBCRITERIA = "SUBCRITERIA", "Subcritérios"
        ALTERNATIVES = "ALTERNATIVES", "Alternativas"

    class Preferred(models.TextChoices):
        LEFT = "LEFT", "Esquerda"
        RIGHT = "RIGHT", "Direita"
        EQUAL = "EQUAL", "Iguais"

    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="comparisons",
    )
    matrix_type = models.CharField(max_length=16, choices=MatrixType.choices)
    parent_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="child_comparisons",
        help_text="Pai dos subcritérios ou critério-folha das alternativas.",
    )
    left_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="as_left_criterion",
    )
    right_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="as_right_criterion",
    )
    left_supplier = models.ForeignKey(
        EvaluationSupplier,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="as_left_supplier",
    )
    right_supplier = models.ForeignKey(
        EvaluationSupplier,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="as_right_supplier",
    )
    preferred = models.CharField(max_length=8, choices=Preferred.choices)
    intensity = models.PositiveSmallIntegerField()
    value = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        help_text="a_left,right na escala de Saaty (recíproco implícito).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comparação pareada"
        indexes = [
            models.Index(fields=["evaluation", "matrix_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.matrix_type} {self.value}"


class ComparisonMatrix(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="matrices",
    )
    matrix_type = models.CharField(max_length=16, choices=PairwiseComparison.MatrixType.choices)
    parent_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    labels = models.JSONField(default=list)
    matrix = models.JSONField(default=list)
    normalized_matrix = models.JSONField(default=list)
    lambda_max = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    ci = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    ri = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    cr = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    is_consistent = models.BooleanField(default=False)
    interpretation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Matriz de comparação"
        unique_together = ("evaluation", "matrix_type", "parent_criterion")


class CriterionWeight(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="criterion_weights",
    )
    evaluation_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        related_name="weights",
    )
    local_weight = models.DecimalField(max_digits=12, decimal_places=6)
    global_weight = models.DecimalField(max_digits=12, decimal_places=6)
    is_leaf = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Peso de critério"
        unique_together = ("evaluation", "evaluation_criterion")


class AlternativePriority(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="alternative_priorities",
    )
    evaluation_supplier = models.ForeignKey(
        EvaluationSupplier,
        on_delete=models.CASCADE,
        related_name="priorities",
    )
    evaluation_criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.CASCADE,
        related_name="alternative_priorities",
    )
    local_priority = models.DecimalField(max_digits=12, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prioridade local"
        unique_together = (
            "evaluation",
            "evaluation_supplier",
            "evaluation_criterion",
        )


class AHPResult(models.Model):
    evaluation = models.OneToOneField(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="ahp_result",
    )
    worst_cr = models.DecimalField(max_digits=12, decimal_places=6)
    all_consistent = models.BooleanField(default=False)
    explanations = models.JSONField(default=list)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resultado AHP"


class Ranking(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="rankings",
    )
    evaluation_supplier = models.ForeignKey(
        EvaluationSupplier,
        on_delete=models.CASCADE,
        related_name="rankings",
    )
    position = models.PositiveSmallIntegerField()
    global_priority = models.DecimalField(max_digits=12, decimal_places=6)
    percent = models.DecimalField(max_digits=8, decimal_places=2)
    is_recommended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ranking"
        unique_together = ("evaluation", "evaluation_supplier")
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.position}º {self.evaluation_supplier}"
