import csv
from io import BytesIO

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from openpyxl import Workbook

from apps.audit.services import log_action
from apps.evaluations.models import Evaluation
from apps.evaluations.views import WIZARD_STEPS, _owned_evaluation
from apps.reports.models import Report
from apps.reports.pdf import build_evaluation_pdf


class ReportPreviewView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        return render(
            request,
            "reports/preview.html",
            {
                "evaluation": evaluation,
                "rankings": evaluation.rankings.select_related("evaluation_supplier"),
                "result": getattr(evaluation, "ahp_result", None),
                "steps": WIZARD_STEPS,
                "current_step": 7,
            },
        )


class ReportPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        content = build_evaluation_pdf(evaluation)
        report = Report.objects.create(evaluation=evaluation, generated_by=request.user)
        report.file.save(f"relatorio_ahp_{evaluation.pk}.pdf", ContentFile(content))
        log_action(
            user=request.user,
            action="gerar_relatorio",
            description=f"Utilizador gerou relatório da avaliação #{evaluation.pk}",
            object_type="Evaluation",
            object_id=evaluation.pk,
            request=request,
        )
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="relatorio_ahp_{evaluation.pk}.pdf"'
        return response


class ReportCSVView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="ranking_ahp_{evaluation.pk}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Posicao", "Fornecedor", "Prioridade", "Percentual", "Recomendado"])
        for rank in evaluation.rankings.select_related("evaluation_supplier"):
            writer.writerow(
                [
                    rank.position,
                    rank.evaluation_supplier.snapshot_name,
                    f"{rank.global_priority:.4f}",
                    f"{rank.percent:.2f}",
                    "Sim" if rank.is_recommended else "Nao",
                ]
            )
        return response


class ReportExcelView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Ranking"
        sheet.append(["Posição", "Fornecedor", "Prioridade", "Percentual", "Recomendado"])
        for rank in evaluation.rankings.select_related("evaluation_supplier"):
            sheet.append(
                [
                    rank.position,
                    rank.evaluation_supplier.snapshot_name,
                    float(rank.global_priority),
                    float(rank.percent),
                    "Sim" if rank.is_recommended else "Não",
                ]
            )
        weights = workbook.create_sheet("Pesos")
        weights.append(["Critério", "Peso local", "Peso global"])
        for item in evaluation.criterion_weights.select_related("evaluation_criterion"):
            weights.append(
                [
                    item.evaluation_criterion.snapshot_name,
                    float(item.local_weight),
                    float(item.global_weight),
                ]
            )
        buffer = BytesIO()
        workbook.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="resultados_ahp_{evaluation.pk}.xlsx"'
        return response
