"""
Serviço de decisão AHP: lê comparações da avaliação, corre o motor
matemático e persiste pesos, consistência, prioridades e ranking.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.ahp.engine import AHPDecisionEngine, AHPError
from apps.ahp.models import RandomIndex
from apps.evaluations.models import (
    AHPResult,
    AlternativePriority,
    ComparisonMatrix,
    CriterionWeight,
    Evaluation,
    EvaluationCriterion,
    EvaluationSupplier,
    PairwiseComparison,
    Ranking,
)

logger = logging.getLogger(__name__)


def _dec(value: float, places: int = 6) -> Decimal:
    return Decimal(str(round(float(value), places)))


def _pair_value(comparison: PairwiseComparison) -> float:
    """Valor a_left,right já persistido."""
    return float(comparison.value)


class EvaluationAHPService:
    """Camada de aplicação entre views/ORM e o motor AHP."""

    def __init__(self, evaluation: Evaluation) -> None:
        threshold = float(getattr(settings, "AHP_CONSISTENCY_THRESHOLD", 0.10))
        self.evaluation = evaluation
        ri_table = {
            item.matrix_size: float(item.value)
            for item in RandomIndex.objects.filter(is_active=True)
        }
        self.engine = AHPDecisionEngine(threshold=threshold, ri_table=ri_table)

    def top_criteria(self):
        return list(
            self.evaluation.evaluation_criteria.filter(parent__isnull=True).order_by(
                "snapshot_code"
            )
        )

    def leaves(self) -> list[EvaluationCriterion]:
        items = []
        for criterion in self.evaluation.evaluation_criteria.select_related("parent"):
            if not criterion.children.exists():
                items.append(criterion)
        return sorted(items, key=lambda c: c.snapshot_code)

    def suppliers(self) -> list[EvaluationSupplier]:
        return list(self.evaluation.evaluation_suppliers.order_by("snapshot_name"))

    def required_pairs(self, labels: list) -> list[tuple]:
        pairs = []
        for i, left in enumerate(labels):
            for right in labels[i + 1 :]:
                pairs.append((left, right))
        return pairs

    def _comparisons(self, matrix_type: str, parent=None):
        qs = self.evaluation.comparisons.filter(matrix_type=matrix_type)
        if parent is None:
            qs = qs.filter(parent_criterion__isnull=True)
        else:
            qs = qs.filter(parent_criterion=parent)
        return qs

    def missing_criterion_pairs(self) -> list[tuple]:
        tops = self.top_criteria()
        existing = {
            tuple(
                sorted(
                    (
                        c.left_criterion_id,
                        c.right_criterion_id,
                    )
                )
            )
            for c in self._comparisons(PairwiseComparison.MatrixType.CRITERIA)
        }
        missing = []
        for a, b in self.required_pairs(tops):
            key = tuple(sorted((a.id, b.id)))
            if key not in existing:
                missing.append((a, b))
        return missing

    def missing_subcriterion_pairs(self, parent: EvaluationCriterion) -> list[tuple]:
        children = list(parent.children.order_by("snapshot_code"))
        existing = {
            tuple(sorted((c.left_criterion_id, c.right_criterion_id)))
            for c in self._comparisons(PairwiseComparison.MatrixType.SUBCRITERIA, parent)
        }
        missing = []
        for a, b in self.required_pairs(children):
            key = tuple(sorted((a.id, b.id)))
            if key not in existing:
                missing.append((a, b))
        return missing

    def missing_alternative_pairs(self, leaf: EvaluationCriterion) -> list[tuple]:
        suppliers = self.suppliers()
        existing = {
            tuple(sorted((c.left_supplier_id, c.right_supplier_id)))
            for c in self._comparisons(PairwiseComparison.MatrixType.ALTERNATIVES, leaf)
        }
        missing = []
        for a, b in self.required_pairs(suppliers):
            key = tuple(sorted((a.id, b.id)))
            if key not in existing:
                missing.append((a, b))
        return missing

    def all_comparisons_complete(self) -> bool:
        if self.missing_criterion_pairs():
            return False
        for parent in self.top_criteria():
            children = list(parent.children.all())
            if len(children) >= 2 and self.missing_subcriterion_pairs(parent):
                return False
        for leaf in self.leaves():
            if self.missing_alternative_pairs(leaf):
                return False
        return True

    def _engine_pairs_from_criteria(self, comparisons) -> list[tuple[str, str, float]]:
        pairs = []
        for cmp in comparisons:
            left = cmp.left_criterion.label
            right = cmp.right_criterion.label
            pairs.append((left, right, _pair_value(cmp)))
        return pairs

    def _engine_pairs_from_suppliers(self, comparisons) -> list[tuple[str, str, float]]:
        pairs = []
        for cmp in comparisons:
            left = cmp.left_supplier.label
            right = cmp.right_supplier.label
            pairs.append((left, right, _pair_value(cmp)))
        return pairs

    def _persist_matrix(
        self, result, matrix_type: str, parent=None
    ) -> ComparisonMatrix:
        cons = result.consistency
        obj, _ = ComparisonMatrix.objects.update_or_create(
            evaluation=self.evaluation,
            matrix_type=matrix_type,
            parent_criterion=parent,
            defaults={
                "labels": result.labels,
                "matrix": result.matrix,
                "normalized_matrix": result.normalized_matrix,
                "lambda_max": _dec(cons.lambda_max),
                "ci": _dec(cons.ci),
                "ri": _dec(cons.ri, 4),
                "cr": _dec(cons.cr),
                "is_consistent": cons.is_consistent,
                "interpretation": cons.interpretation,
            },
        )
        return obj

    @transaction.atomic
    def compute(self) -> AHPResult:
        evaluation = Evaluation.objects.select_for_update().get(pk=self.evaluation.pk)
        self.evaluation = evaluation
        if not self.all_comparisons_complete():
            raise AHPError("Existem comparações pareadas incompletas.")

        tops = self.top_criteria()
        if len(tops) < 2:
            raise AHPError("São necessários pelo menos 2 critérios.")
        suppliers = self.suppliers()
        if len(suppliers) < 2:
            raise AHPError("São necessários pelo menos 2 fornecedores.")

        crit_result = self.engine.solve_matrix(
            [c.label for c in tops],
            self._engine_pairs_from_criteria(
                self._comparisons(PairwiseComparison.MatrixType.CRITERIA)
            ),
        )
        self._persist_matrix(crit_result, PairwiseComparison.MatrixType.CRITERIA)
        criterion_weights = crit_result.weights

        sub_weights: dict[str, dict[str, float]] = {}
        parent_of: dict[str, str | None] = {}
        for top in tops:
            children = list(top.children.order_by("snapshot_code"))
            if len(children) >= 2:
                sub_result = self.engine.solve_matrix(
                    [c.label for c in children],
                    self._engine_pairs_from_criteria(
                        self._comparisons(
                            PairwiseComparison.MatrixType.SUBCRITERIA, top
                        )
                    ),
                )
                self._persist_matrix(
                    sub_result, PairwiseComparison.MatrixType.SUBCRITERIA, top
                )
                sub_weights[top.label] = sub_result.weights
                for child in children:
                    parent_of[child.label] = top.label
            elif len(children) == 1:
                sub_weights[top.label] = {children[0].label: 1.0}
                parent_of[children[0].label] = top.label
            else:
                parent_of[top.label] = None

        leaves = self.leaves()
        leaf_labels = [leaf.label for leaf in leaves]
        leaf_global = self.engine.compose_leaf_weights(
            criterion_weights, sub_weights, leaf_labels, parent_of
        )

        CriterionWeight.objects.filter(evaluation=evaluation).delete()
        by_label = {c.label: c for c in evaluation.evaluation_criteria.all()}
        for criterion in evaluation.evaluation_criteria.all():
            is_leaf = criterion.label in leaf_global
            if criterion.parent_id is None:
                local = criterion_weights.get(criterion.label, 0.0)
                global_w = (
                    leaf_global.get(criterion.label, 0.0)
                    if is_leaf
                    else local
                )
            else:
                parent_label = criterion.parent.label
                local = sub_weights.get(parent_label, {}).get(criterion.label, 0.0)
                global_w = leaf_global.get(criterion.label, 0.0)
            CriterionWeight.objects.create(
                evaluation=evaluation,
                evaluation_criterion=criterion,
                local_weight=_dec(local),
                global_weight=_dec(global_w),
                is_leaf=is_leaf,
            )

        local_priorities: dict[str, dict[str, float]] = {}
        AlternativePriority.objects.filter(evaluation=evaluation).delete()
        all_consistent = crit_result.consistency.is_consistent
        worst_cr = crit_result.consistency.cr

        for leaf in leaves:
            alt_result = self.engine.solve_matrix(
                [s.label for s in suppliers],
                self._engine_pairs_from_suppliers(
                    self._comparisons(PairwiseComparison.MatrixType.ALTERNATIVES, leaf)
                ),
            )
            self._persist_matrix(
                alt_result, PairwiseComparison.MatrixType.ALTERNATIVES, leaf
            )
            local_priorities[leaf.label] = alt_result.weights
            all_consistent = all_consistent and alt_result.consistency.is_consistent
            worst_cr = max(worst_cr, alt_result.consistency.cr)
            for supplier in suppliers:
                AlternativePriority.objects.create(
                    evaluation=evaluation,
                    evaluation_supplier=supplier,
                    evaluation_criterion=leaf,
                    local_priority=_dec(alt_result.weights[supplier.label]),
                )

        for parent, mapping in sub_weights.items():
            # sub-matrizes já persistidas; atualiza worst_cr via ComparisonMatrix
            pass

        for matrix in evaluation.matrices.all():
            if matrix.cr is not None:
                worst_cr = max(worst_cr, float(matrix.cr))
            all_consistent = all_consistent and matrix.is_consistent

        scores = self.engine.ranking_calculator.global_priorities(
            [s.label for s in suppliers],
            leaf_global,
            local_priorities,
        )
        ranking_rows = self.engine.ranking_calculator.rank(scores)
        Ranking.objects.filter(evaluation=evaluation).delete()
        suppliers_by_label = {s.label: s for s in suppliers}
        recommended_name = ranking_rows[0]["label"] if ranking_rows else ""
        for row in ranking_rows:
            Ranking.objects.create(
                evaluation=evaluation,
                evaluation_supplier=suppliers_by_label[row["label"]],
                position=row["position"],
                global_priority=_dec(row["score"]),
                percent=_dec(row["percent"], 2),
                is_recommended=row["recommended"],
            )

        explanations = [
            crit_result.explanations[0],
            (
                f"O fornecedor {recommended_name} obteve prioridade global de "
                f"{ranking_rows[0]['percent']:.2f}%, ficando em primeiro lugar."
                if ranking_rows
                else ""
            ),
            (
                f"A pior razão de consistência observada foi CR = {worst_cr:.4f}, "
                + (
                    "indicando consistência aceitável."
                    if all_consistent
                    else "indicando que pelo menos uma matriz é inconsistente."
                )
            ),
        ]
        payload = {
            "criterion_weights": criterion_weights,
            "leaf_global_weights": leaf_global,
            "local_priorities": local_priorities,
            "global_scores": scores,
            "ranking": ranking_rows,
        }
        result_obj, _ = AHPResult.objects.update_or_create(
            evaluation=evaluation,
            defaults={
                "worst_cr": _dec(worst_cr),
                "all_consistent": all_consistent,
                "explanations": [e for e in explanations if e],
                "payload": payload,
            },
        )
        if all_consistent:
            if evaluation.status != Evaluation.Status.COMPLETED:
                evaluation.status = Evaluation.Status.IN_PROGRESS
        else:
            evaluation.status = Evaluation.Status.INCONSISTENT
        evaluation.save(update_fields=["status", "updated_at"])
        logger.info("AHP calculado para avaliação %s (CR pior=%.4f)", evaluation.pk, worst_cr)
        return result_obj
