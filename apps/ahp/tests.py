from django.test import SimpleTestCase

from apps.ahp.engine import AHPDecisionEngine, AHPMatrix, RankingCalculator


class AHPEngineTests(SimpleTestCase):
    """Caso conhecido: matriz consistente com prioridades 0.6, 0.3 e 0.1."""

    def test_known_consistent_matrix_weights_and_cr(self):
        matrix = AHPMatrix(["Técnica", "Experiência", "Custo"])
        matrix.set_comparison("Técnica", "Experiência", 2)
        matrix.set_comparison("Técnica", "Custo", 6)
        matrix.set_comparison("Experiência", "Custo", 3)
        result = matrix.solve()
        self.assertAlmostEqual(result.weights["Técnica"], 0.6, places=4)
        self.assertAlmostEqual(result.weights["Experiência"], 0.3, places=4)
        self.assertAlmostEqual(result.weights["Custo"], 0.1, places=4)
        self.assertAlmostEqual(result.consistency.lambda_max, 3.0, places=4)
        self.assertAlmostEqual(result.consistency.ci, 0.0, places=4)
        self.assertAlmostEqual(result.consistency.cr, 0.0, places=4)

    def test_reciprocity_is_automatic(self):
        matrix = AHPMatrix(["A", "B"])
        matrix.set_comparison("A", "B", 5)
        self.assertEqual(matrix.array[0, 1], 5)
        self.assertAlmostEqual(matrix.array[1, 0], 0.2)

    def test_global_ranking_is_normalized(self):
        scores = RankingCalculator().global_priorities(
            ["Fornecedor A", "Fornecedor B"],
            {"Técnica": 0.75, "Custo": 0.25},
            {"Técnica": {"Fornecedor A": 0.8, "Fornecedor B": 0.2}, "Custo": {"Fornecedor A": 0.4, "Fornecedor B": 0.6}},
        )
        ranking = RankingCalculator().rank(scores)
        self.assertAlmostEqual(sum(scores.values()), 1.0)
        self.assertEqual(ranking[0]["label"], "Fornecedor A")
