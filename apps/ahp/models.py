from django.core.validators import MinValueValidator
from django.db import models


class RandomIndex(models.Model):
    """Índice aleatório (RI) de Saaty, administrável sem mudar o código."""

    matrix_size = models.PositiveSmallIntegerField(
        "Ordem da matriz (n)",
        unique=True,
        validators=[MinValueValidator(1)],
    )
    value = models.DecimalField(
        "Índice aleatório (RI)",
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField("Ativo", default=True)
    source = models.CharField("Fonte/observação", max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Índice aleatório (RI)"
        verbose_name_plural = "Tabela de índices aleatórios (RI)"
        ordering = ["matrix_size"]

    def __str__(self) -> str:
        return f"n={self.matrix_size}: RI={self.value}"
