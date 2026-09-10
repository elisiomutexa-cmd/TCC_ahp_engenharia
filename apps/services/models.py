"""Serviços de engenharia a contratar."""

from django.db import models


class EngineeringService(models.Model):
    class ServiceType(models.TextChoices):
        HVAC = "HVAC", "Ar condicionado/HVAC"
        ELECTRICAL = "ELECTRICAL", "Rede elétrica"
        HOSPITAL = "HOSPITAL", "Equipamentos hospitalares"
        DATA_NETWORK = "DATA_NETWORK", "Rede de dados"
        BUILDING = "BUILDING", "Manutenção predial"
        OTHER = "OTHER", "Outros"

    class Priority(models.TextChoices):
        LOW = "LOW", "Baixa"
        MEDIUM = "MEDIUM", "Média"
        HIGH = "HIGH", "Alta"
        CRITICAL = "CRITICAL", "Crítica"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberto"
        IN_PROGRESS = "IN_PROGRESS", "Em curso"
        CLOSED = "CLOSED", "Encerrado"
        CANCELLED = "CANCELLED", "Cancelado"

    name = models.CharField("Nome", max_length=200)
    service_type = models.CharField(
        "Tipo de serviço",
        max_length=20,
        choices=ServiceType.choices,
        db_index=True,
    )
    description = models.TextField("Descrição", blank=True)
    location = models.CharField("Local", max_length=180, blank=True)
    priority = models.CharField(
        "Prioridade",
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    requested_at = models.DateField("Data da solicitação")
    deadline = models.DateField("Prazo", null=True, blank=True)
    status = models.CharField(
        "Estado",
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    is_demo = models.BooleanField("Dados de demonstração", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Serviço de engenharia"
        verbose_name_plural = "Serviços de engenharia"
        ordering = ["-requested_at", "name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self) -> str:
        return self.name
