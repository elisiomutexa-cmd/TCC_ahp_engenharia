"""Utilizadores do SAD: Administrador e Gestor/Avaliador."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        EVALUATOR = "EVALUATOR", "Gestor/Avaliador"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EVALUATOR,
        db_index=True,
    )
    phone = models.CharField("Telefone", max_length=30, blank=True)
    job_title = models.CharField("Cargo", max_length=120, blank=True)
    organization = models.CharField("Organização", max_length=180, blank=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Utilizador"
        verbose_name_plural = "Utilizadores"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_administrator(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_evaluator(self) -> bool:
        return self.role == self.Role.EVALUATOR
