"""Critérios e subcritérios AHP (hierarquia dinâmica, não hard-coded)."""

from django.db import models


class Criterion(models.Model):
    class Kind(models.TextChoices):
        BENEFIT = "BENEFIT", "Benefício (maior é melhor)"
        COST = "COST", "Custo (menor é melhor)"

    code = models.CharField("Código", max_length=20)
    name = models.CharField("Nome", max_length=160)
    description = models.TextField("Descrição", blank=True)
    kind = models.CharField(
        "Tipo",
        max_length=16,
        choices=Kind.choices,
        default=Kind.BENEFIT,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Critério pai",
    )
    catalog_weight = models.DecimalField(
        "Peso de catálogo (opcional)",
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Peso informativo no catálogo. O peso da decisão é calculado pelo AHP.",
    )
    is_active = models.BooleanField("Ativo", default=True, db_index=True)
    sort_order = models.PositiveIntegerField("Ordem", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Critério"
        verbose_name_plural = "Critérios"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "parent"],
                name="uniq_criterion_code_per_parent",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "parent"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    @property
    def is_subcriterion(self) -> bool:
        return self.parent_id is not None
