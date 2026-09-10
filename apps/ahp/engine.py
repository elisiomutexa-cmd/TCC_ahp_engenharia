"""
Motor matemático do Analytic Hierarchy Process (AHP).

Implementa a escala fundamental de Saaty, normalização da matriz de
comparação pareada, vetor de prioridades (média das linhas da matriz
normalizada), λmax, CI, RI e CR = CI / RI.

Este módulo não depende de Django e pode ser testado isoladamente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

SAATY_SCALE: dict[int, str] = {
    1: "Importância igual",
    2: "Importância ligeiramente maior",
    3: "Importância moderada",
    4: "Importância entre moderada e forte",
    5: "Importância forte",
    6: "Importância entre forte e muito forte",
    7: "Importância muito forte",
    8: "Importância entre muito forte e extrema",
    9: "Importância extrema",
}

# Índice aleatório (Saaty). n=1 e n=2 são triviais (CR = 0).
DEFAULT_RI_TABLE: dict[int, float] = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}

CONSISTENCY_THRESHOLD = 0.10
WEIGHT_TOLERANCE = 1e-6


class AHPError(ValueError):
    """Erro de domínio no cálculo AHP."""


def saaty_value(intensity: int, preferred_is_first: bool) -> float:
    """Converte intensidade 1–9 e lado preferido no valor a_ij."""
    if intensity not in SAATY_SCALE:
        raise AHPError(f"Intensidade inválida na escala de Saaty: {intensity}")
    if intensity == 1:
        return 1.0
    return float(intensity) if preferred_is_first else 1.0 / float(intensity)


@dataclass
class ConsistencyResult:
    lambda_max: float
    ci: float
    ri: float
    cr: float
    n: int
    is_applicable: bool
    is_consistent: bool
    interpretation: str

    def as_dict(self) -> dict:
        return {
            "lambda_max": round(self.lambda_max, 6),
            "ci": round(self.ci, 6),
            "ri": round(self.ri, 4),
            "cr": round(self.cr, 6),
            "n": self.n,
            "is_applicable": self.is_applicable,
            "is_consistent": self.is_consistent,
            "interpretation": self.interpretation,
        }


@dataclass
class AHPResult:
    labels: list[str]
    matrix: list[list[float]]
    normalized_matrix: list[list[float]]
    weights: dict[str, float]
    consistency: ConsistencyResult
    explanations: list[str] = field(default_factory=list)

    def weight_list(self) -> list[float]:
        return [self.weights[label] for label in self.labels]


class ConsistencyCalculator:
    """Calcula λmax, CI, RI e CR = CI / RI."""

    def __init__(
        self,
        ri_table: dict[int, float] | None = None,
        threshold: float = CONSISTENCY_THRESHOLD,
    ) -> None:
        self.ri_table = dict(DEFAULT_RI_TABLE)
        if ri_table:
            self.ri_table.update(ri_table)
        self.threshold = threshold

    def random_index(self, n: int) -> float:
        if n in self.ri_table:
            return self.ri_table[n]
        # Extensão linear conservadora para n > 15.
        if n > 15:
            return max(self.ri_table.values())
        raise AHPError(f"RI não definido para n={n}. Estenda a tabela RI.")

    def calculate(self, matrix: np.ndarray, weights: np.ndarray) -> ConsistencyResult:
        n = matrix.shape[0]
        aw = matrix @ weights
        # Evita divisão por zero em pesos nulos (não deve ocorrer em AHP válido).
        ratios = []
        for i in range(n):
            if weights[i] <= 0:
                raise AHPError("Peso nulo ou negativo — matriz inválida.")
            ratios.append(aw[i] / weights[i])
        lambda_max = float(np.mean(ratios))

        if n <= 2:
            return ConsistencyResult(
                lambda_max=lambda_max,
                ci=0.0,
                ri=0.0,
                cr=0.0,
                n=n,
                is_applicable=False,
                is_consistent=True,
                interpretation=(
                    "Para n ≤ 2 a matriz é sempre consistente "
                    "(CR convencional não se aplica)."
                ),
            )

        ci = (lambda_max - n) / (n - 1)
        ri = self.random_index(n)
        if ri == 0:
            cr = 0.0
        else:
            cr = ci / ri  # CR = CI / RI (nunca RI / CI)

        is_consistent = cr < self.threshold
        if is_consistent:
            interpretation = (
                f"Razão de Consistência = {cr:.4f}. "
                "Matriz considerada consistente."
            )
        else:
            interpretation = (
                f"Razão de Consistência = {cr:.4f}. "
                "A matriz apresenta inconsistência. Revise as comparações."
            )
        return ConsistencyResult(
            lambda_max=lambda_max,
            ci=ci,
            ri=ri,
            cr=cr,
            n=n,
            is_applicable=True,
            is_consistent=is_consistent,
            interpretation=interpretation,
        )


class AHPWeightCalculator:
    """Normaliza a matriz e obtém o vetor de prioridades (média das linhas)."""

    def compute(self, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        col_sums = matrix.sum(axis=0)
        if np.any(col_sums <= 0):
            raise AHPError("Soma de coluna inválida na matriz AHP.")
        normalized = matrix / col_sums
        weights = normalized.mean(axis=1)
        total = weights.sum()
        if total <= 0:
            raise AHPError("Vetor de pesos inválido.")
        weights = weights / total
        return normalized, weights


class AHPMatrix:
    """Matriz de comparação pareada n×n com reciprocidade aij = 1/aji e aii = 1."""

    def __init__(self, labels: Sequence[str]) -> None:
        if len(labels) < 2:
            raise AHPError("São necessárias pelo menos 2 alternativas/critérios.")
        if len(set(labels)) != len(labels):
            raise AHPError("Os rótulos da matriz devem ser únicos.")
        self.labels = list(labels)
        n = len(self.labels)
        self._matrix = np.eye(n, dtype=float)
        self._index = {label: i for i, label in enumerate(self.labels)}

    @property
    def n(self) -> int:
        return len(self.labels)

    @property
    def array(self) -> np.ndarray:
        return self._matrix.copy()

    def set_comparison(self, a: str, b: str, value: float) -> None:
        if a == b:
            if not math.isclose(value, 1.0, rel_tol=1e-9):
                raise AHPError("A diagonal da matriz deve ser 1.")
            return
        if value <= 0:
            raise AHPError("Valores de comparação devem ser positivos.")
        i, j = self._index[a], self._index[b]
        self._matrix[i, j] = float(value)
        self._matrix[j, i] = 1.0 / float(value)

    def set_saaty(self, a: str, b: str, intensity: int, a_preferred: bool) -> None:
        if intensity == 1:
            self.set_comparison(a, b, 1.0)
            return
        value = saaty_value(intensity, a_preferred)
        self.set_comparison(a, b, value)

    def is_complete(self) -> bool:
        return bool(np.all(self._matrix > 0))

    def validate_reciprocity(self, tol: float = 1e-9) -> None:
        n = self.n
        for i in range(n):
            if not math.isclose(self._matrix[i, i], 1.0, rel_tol=tol, abs_tol=tol):
                raise AHPError("Elementos da diagonal devem ser 1.")
            for j in range(i + 1, n):
                expected = 1.0 / self._matrix[i, j]
                if not math.isclose(self._matrix[j, i], expected, rel_tol=1e-6, abs_tol=1e-9):
                    raise AHPError("A matriz não respeita aij = 1/aji.")

    def solve(
        self,
        consistency: ConsistencyCalculator | None = None,
        threshold: float = CONSISTENCY_THRESHOLD,
    ) -> AHPResult:
        if not self.is_complete():
            raise AHPError("A matriz de comparação está incompleta.")
        self.validate_reciprocity()
        calculator = AHPWeightCalculator()
        normalized, weights = calculator.compute(self._matrix)
        cons = (consistency or ConsistencyCalculator(threshold=threshold)).calculate(
            self._matrix, weights
        )
        weight_map = {label: float(weights[i]) for i, label in enumerate(self.labels)}
        if not math.isclose(sum(weight_map.values()), 1.0, abs_tol=WEIGHT_TOLERANCE):
            raise AHPError("A soma dos pesos deve ser aproximadamente 1.")

        top_label = max(weight_map, key=weight_map.get)
        explanations = [
            (
                f"{top_label} recebeu peso de {weight_map[top_label] * 100:.2f}% "
                "e foi o elemento de maior importância nesta matriz."
            ),
            cons.interpretation,
        ]
        return AHPResult(
            labels=list(self.labels),
            matrix=self._matrix.tolist(),
            normalized_matrix=normalized.tolist(),
            weights=weight_map,
            consistency=cons,
            explanations=explanations,
        )


class RankingCalculator:
    """Calcula prioridades globais e ranking a partir de pesos e prioridades locais."""

    def global_priorities(
        self,
        alternatives: Sequence[str],
        leaf_weights: dict[str, float],
        local_priorities: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """
        P(A) = Σ peso(folha) × prioridade_local(A, folha)

        `leaf_weights` já deve incorporar o peso do critério-pai quando houver
        subcritérios (peso_global_folha = peso_pai × peso_sub).
        """
        scores = {alt: 0.0 for alt in alternatives}
        for leaf, w_leaf in leaf_weights.items():
            locals_for_leaf = local_priorities.get(leaf) or {}
            for alt in alternatives:
                scores[alt] += w_leaf * locals_for_leaf.get(alt, 0.0)
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        return scores

    def rank(self, scores: dict[str, float]) -> list[dict]:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ranking = []
        for position, (label, score) in enumerate(ordered, start=1):
            ranking.append(
                {
                    "position": position,
                    "label": label,
                    "score": score,
                    "percent": score * 100.0,
                    "recommended": position == 1,
                }
            )
        return ranking


class AHPDecisionEngine:
    """Orquestra matrizes de critérios, subcritérios e alternativas."""

    def __init__(
        self,
        threshold: float = CONSISTENCY_THRESHOLD,
        ri_table: dict[int, float] | None = None,
    ) -> None:
        self.threshold = threshold
        self.consistency = ConsistencyCalculator(
            ri_table=ri_table,
            threshold=threshold,
        )
        self.ranking_calculator = RankingCalculator()

    def solve_matrix(
        self,
        labels: Sequence[str],
        pairs: Sequence[tuple[str, str, float]],
    ) -> AHPResult:
        matrix = AHPMatrix(labels)
        for a, b, value in pairs:
            matrix.set_comparison(a, b, value)
        return matrix.solve(consistency=self.consistency, threshold=self.threshold)

    def compose_leaf_weights(
        self,
        criterion_weights: dict[str, float],
        subcriterion_weights: dict[str, dict[str, float]],
        leaves: Sequence[str],
        parent_of: dict[str, str | None],
    ) -> dict[str, float]:
        """
        Folha de primeiro nível: peso do critério.
        Folha-subcritério: peso(pai) × peso(sub | pai).
        """
        result: dict[str, float] = {}
        for leaf in leaves:
            parent = parent_of.get(leaf)
            if parent:
                w_parent = criterion_weights.get(parent, 0.0)
                w_sub = subcriterion_weights.get(parent, {}).get(leaf, 0.0)
                result[leaf] = w_parent * w_sub
            else:
                result[leaf] = criterion_weights.get(leaf, 0.0)
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result
