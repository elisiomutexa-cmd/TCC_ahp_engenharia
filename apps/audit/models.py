"""Registo de auditoria das ações do sistema."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Utilizador",
    )
    action = models.CharField("Ação", max_length=80, db_index=True)
    object_type = models.CharField("Tipo de objeto", max_length=80, blank=True)
    object_id = models.CharField("ID do objeto", max_length=64, blank=True)
    description = models.TextField("Descrição")
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Registo de auditoria"
        verbose_name_plural = "Registos de auditoria"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} — {self.created_at:%Y-%m-%d %H:%M}"
