"""Fornecedores de serviços de engenharia."""

from django.db import models


class Supplier(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativo"
        INACTIVE = "INACTIVE", "Inativo"

    name = models.CharField("Nome da empresa", max_length=180)
    nuit = models.CharField("NUIT", max_length=20, unique=True)
    email = models.EmailField("Email")
    phone = models.CharField("Telefone", max_length=30)
    address = models.CharField("Endereço", max_length=255, blank=True)
    city = models.CharField("Cidade", max_length=80, blank=True)
    province = models.CharField("Província", max_length=80, blank=True)
    contact_person = models.CharField("Responsável", max_length=120, blank=True)
    specialties = models.TextField("Especialidades", blank=True)
    experience_years = models.PositiveIntegerField("Anos de experiência", default=0)
    certifications = models.TextField("Certificações", blank=True)
    status = models.CharField(
        "Estado",
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    is_demo = models.BooleanField("Dados de demonstração", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["status", "name"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE
