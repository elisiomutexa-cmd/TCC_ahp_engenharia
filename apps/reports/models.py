from django.conf import settings
from django.db import models

from apps.evaluations.models import Evaluation


class Report(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
    )
    file = models.FileField("Ficheiro PDF", upload_to="reports/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Relatório"
        verbose_name_plural = "Relatórios"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Relatório avaliação #{self.evaluation_id}"
