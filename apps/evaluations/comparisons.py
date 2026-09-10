"""Persistência de comparações pareadas (escala de Saaty)."""

from decimal import Decimal, ROUND_HALF_UP

from apps.evaluations.models import PairwiseComparison


def saaty_matrix_value(preferred: str, intensity: int) -> Decimal:
    intensity = int(intensity)
    if intensity < 1 or intensity > 9:
        raise ValueError("Intensidade deve estar entre 1 e 9.")
    if preferred == PairwiseComparison.Preferred.EQUAL or intensity == 1:
        return Decimal("1")
    if preferred == PairwiseComparison.Preferred.LEFT:
        return Decimal(intensity)
    if preferred == PairwiseComparison.Preferred.RIGHT:
        return (Decimal("1") / Decimal(intensity)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    raise ValueError("Preferência inválida.")


def upsert_criterion_comparison(
    *,
    evaluation,
    matrix_type: str,
    left,
    right,
    preferred: str,
    intensity: int,
    parent=None,
) -> PairwiseComparison:
    value = saaty_matrix_value(preferred, intensity)
    obj, _ = PairwiseComparison.objects.update_or_create(
        evaluation=evaluation,
        matrix_type=matrix_type,
        parent_criterion=parent,
        left_criterion=left,
        right_criterion=right,
        defaults={
            "left_supplier": None,
            "right_supplier": None,
            "preferred": preferred,
            "intensity": 1 if preferred == PairwiseComparison.Preferred.EQUAL else intensity,
            "value": value,
        },
    )
    return obj


def upsert_supplier_comparison(
    *,
    evaluation,
    leaf,
    left,
    right,
    preferred: str,
    intensity: int,
) -> PairwiseComparison:
    value = saaty_matrix_value(preferred, intensity)
    obj, _ = PairwiseComparison.objects.update_or_create(
        evaluation=evaluation,
        matrix_type=PairwiseComparison.MatrixType.ALTERNATIVES,
        parent_criterion=leaf,
        left_supplier=left,
        right_supplier=right,
        defaults={
            "left_criterion": None,
            "right_criterion": None,
            "preferred": preferred,
            "intensity": 1 if preferred == PairwiseComparison.Preferred.EQUAL else intensity,
            "value": value,
        },
    )
    return obj
