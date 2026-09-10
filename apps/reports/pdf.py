"""Geração de relatório PDF profissional da decisão AHP."""

from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0b3a5b")
BLUE = colors.HexColor("#1a6aa3")
LIGHT = colors.HexColor("#e8f1f8")
GREEN = colors.HexColor("#1f7a4d")
CHART_COLORS = [NAVY, BLUE, GREEN, colors.HexColor("#c9a227"), colors.HexColor("#64748b")]


def _ranking_chart(evaluation):
    rows = list(evaluation.rankings.select_related("evaluation_supplier"))
    if not rows:
        return None
    drawing = Drawing(460, 220)
    chart = Pie()
    chart.x, chart.y = 150, 15
    chart.width, chart.height = 180, 180
    chart.data = [float(row.percent) for row in rows]
    chart.labels = [row.evaluation_supplier.snapshot_name for row in rows]
    chart.sideLabels = True
    for index in range(len(rows)):
        chart.slices[index].fillColor = CHART_COLORS[index % len(CHART_COLORS)]
    drawing.add(chart)
    drawing.add(String(0, 202, "Distribuição da prioridade global dos fornecedores (%)", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    return drawing


def _weights_chart(evaluation):
    rows = list(
        evaluation.criterion_weights.select_related("evaluation_criterion").filter(is_leaf=True)
    )
    if not rows:
        return None
    drawing = Drawing(460, 220)
    chart = VerticalBarChart()
    chart.x, chart.y = 40, 35
    chart.width, chart.height = 380, 145
    chart.data = [[float(row.global_weight) * 100 for row in rows]]
    chart.categoryAxis.categoryNames = [row.evaluation_criterion.snapshot_code for row in rows]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(100, max(chart.data[0]) * 1.2)
    chart.valueAxis.valueStep = max(10, round(chart.valueAxis.valueMax / 5))
    chart.bars[0].fillColor = BLUE
    drawing.add(chart)
    drawing.add(String(0, 202, "Pesos globais dos critérios-folha (%)", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    return drawing


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontSize=22,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverSub",
            parent=styles["Normal"],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=BLUE,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            textColor=NAVY,
            fontSize=13,
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyJust",
            parent=styles["Normal"],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#445"),
        )
    )
    return styles


def _table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9bb7cc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_evaluation_pdf(evaluation) -> bytes:
    buffer = BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"Relatório AHP — Avaliação {evaluation.pk}",
    )
    story = []
    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph("Relatório de Apoio à Decisão", styles["CoverTitle"]))
    story.append(
        Paragraph(
            "Processo Analítico Hierárquico (AHP) — Saaty",
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(f"<b>Serviço:</b> {evaluation.service.name}", styles["CoverSub"]))
    story.append(
        Paragraph(
            f"<b>Data:</b> {timezone.localtime(evaluation.created_at).strftime('%d/%m/%Y %H:%M')}",
            styles["CoverSub"],
        )
    )
    story.append(
        Paragraph(f"<b>Avaliador:</b> {evaluation.evaluator}", styles["CoverSub"])
    )
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        Paragraph(
            "Artefacto tecnológico de Sistema de Apoio à Decisão (SAD) para "
            "contratação de serviços de engenharia. Os resultados foram obtidos "
            "exclusivamente pelo método AHP (matrizes pareadas, vetor de prioridades "
            "e razão de consistência CR = CI / RI).",
            styles["BodyJust"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("1. Objetivo da decisão", styles["Section"]))
    story.append(Paragraph(evaluation.objective, styles["BodyJust"]))

    story.append(Paragraph("2. Fornecedores avaliados", styles["Section"]))
    rows = [["Fornecedor", "NUIT"]]
    for item in evaluation.evaluation_suppliers.select_related("supplier"):
        rows.append([item.snapshot_name, item.supplier.nuit])
    story.append(_table(rows, [12 * cm, 5 * cm]))

    story.append(Paragraph("3. Critérios", styles["Section"]))
    rows = [["Código", "Nome", "Nível"]]
    for item in evaluation.evaluation_criteria.select_related("parent"):
        level = "Subcritério" if item.parent_id else "Critério"
        rows.append([item.snapshot_code, item.snapshot_name, level])
    story.append(_table(rows, [3 * cm, 10 * cm, 4 * cm]))

    story.append(Paragraph("4. Estrutura hierárquica", styles["Section"]))
    story.append(
        Paragraph(
            "Objetivo → Critérios → Subcritérios (quando aplicável) → Alternativas (fornecedores).",
            styles["BodyJust"],
        )
    )
    for parent in evaluation.evaluation_criteria.filter(parent__isnull=True):
        children = list(parent.children.all())
        if children:
            story.append(
                Paragraph(
                    f"<b>{parent.snapshot_code} {parent.snapshot_name}</b>: "
                    + ", ".join(c.snapshot_name for c in children),
                    styles["Small"],
                )
            )
        else:
            story.append(
                Paragraph(
                    f"<b>{parent.snapshot_code} {parent.snapshot_name}</b> (sem subcritérios)",
                    styles["Small"],
                )
            )

    story.append(Paragraph("5. Comparação dos critérios", styles["Section"]))
    matrix = evaluation.matrices.filter(matrix_type="CRITERIA", parent_criterion__isnull=True).first()
    if matrix:
        header = [""] + matrix.labels
        data = [header]
        for i, label in enumerate(matrix.labels):
            row = [label] + [f"{v:.4f}" for v in matrix.matrix[i]]
            data.append(row)
        story.append(_table(data))

    story.append(Paragraph("6. Pesos dos critérios", styles["Section"]))
    rows = [["Critério", "Peso local", "Peso global", "Folha?"]]
    for weight in evaluation.criterion_weights.select_related("evaluation_criterion"):
        rows.append(
            [
                weight.evaluation_criterion.snapshot_name,
                f"{weight.local_weight:.4f}",
                f"{weight.global_weight:.4f}",
                "Sim" if weight.is_leaf else "Não",
            ]
        )
    story.append(_table(rows, [7 * cm, 3.5 * cm, 3.5 * cm, 3 * cm]))
    weights_chart = _weights_chart(evaluation)
    if weights_chart:
        story.append(Spacer(1, 0.25 * cm))
        story.append(weights_chart)

    story.append(Paragraph("7. Consistência", styles["Section"]))
    rows = [["Matriz", "n", "λmax", "CI", "RI", "CR", "Situação"]]
    for item in evaluation.matrices.all():
        name = item.get_matrix_type_display()
        if item.parent_criterion_id:
            name = f"{name} ({item.parent_criterion.snapshot_name})"
        rows.append(
            [
                name,
                str(len(item.labels)),
                f"{item.lambda_max:.4f}" if item.lambda_max is not None else "—",
                f"{item.ci:.4f}" if item.ci is not None else "—",
                f"{item.ri:.4f}" if item.ri is not None else "—",
                f"{item.cr:.4f}" if item.cr is not None else "—",
                "Consistente" if item.is_consistent else "Inconsistente",
            ]
        )
    story.append(_table(rows))
    result = getattr(evaluation, "ahp_result", None)
    if result:
        for text in result.explanations:
            story.append(Paragraph(text, styles["BodyJust"]))

    story.append(Paragraph("8. Comparações das alternativas", styles["Section"]))
    story.append(
        Paragraph(
            "Para cada critério-folha os fornecedores foram comparados na escala fundamental de Saaty (1–9).",
            styles["BodyJust"],
        )
    )

    story.append(Paragraph("9. Prioridades locais", styles["Section"]))
    rows = [["Fornecedor", "Critério", "Prioridade local"]]
    for prio in evaluation.alternative_priorities.select_related(
        "evaluation_supplier", "evaluation_criterion"
    ):
        rows.append(
            [
                prio.evaluation_supplier.snapshot_name,
                prio.evaluation_criterion.snapshot_name,
                f"{prio.local_priority:.4f}",
            ]
        )
    story.append(_table(rows, [6 * cm, 7 * cm, 4 * cm]))

    story.append(Paragraph("10. Prioridades globais", styles["Section"]))
    story.append(
        Paragraph(
            "P(A) = Σ peso_global(folha) × prioridade_local(A, folha). "
            "O vetor resultante é normalizado para soma 1.",
            styles["BodyJust"],
        )
    )

    story.append(Paragraph("11. Ranking final", styles["Section"]))
    rows = [["Posição", "Fornecedor", "Prioridade", "Percentual", "Situação"]]
    for rank in evaluation.rankings.select_related("evaluation_supplier"):
        rows.append(
            [
                f"{rank.position}º",
                rank.evaluation_supplier.snapshot_name,
                f"{rank.global_priority:.4f}",
                f"{rank.percent:.2f}%",
                "Recomendado" if rank.is_recommended else "—",
            ]
        )
    story.append(_table(rows, [2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2.5 * cm]))
    ranking_chart = _ranking_chart(evaluation)
    if ranking_chart:
        story.append(Spacer(1, 0.25 * cm))
        story.append(ranking_chart)

    story.append(Paragraph("12. Fornecedor recomendado", styles["Section"]))
    winner = evaluation.rankings.filter(is_recommended=True).select_related(
        "evaluation_supplier"
    ).first()
    if winner:
        story.append(
            Paragraph(
                f"<b>{winner.evaluation_supplier.snapshot_name}</b> — pontuação {winner.percent:.2f}%.",
                styles["BodyJust"],
            )
        )

    story.append(Paragraph("13. Observações", styles["Section"]))
    story.append(Paragraph(evaluation.notes or "Sem observações adicionais.", styles["BodyJust"]))

    story.append(Paragraph("14. Data e responsável", styles["Section"]))
    completed = (
        timezone.localtime(evaluation.completed_at).strftime("%d/%m/%Y %H:%M")
        if evaluation.completed_at
        else "Avaliação ainda não concluída"
    )
    story.append(
        Paragraph(
            f"Responsável: {evaluation.evaluator}. Data de conclusão: {completed}. "
            f"Estado: {evaluation.get_status_display()}.",
            styles["BodyJust"],
        )
    )
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        Paragraph(
            "Documento gerado automaticamente pelo SAD AHP Engenharia. "
            "Os cálculos respeitam aij = 1/aji, aii = 1 e CR = CI/RI.",
            styles["Small"],
        )
    )
    doc.build(story)
    return buffer.getvalue()
