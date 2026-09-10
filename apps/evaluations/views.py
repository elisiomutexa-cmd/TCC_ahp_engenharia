"""Assistente AHP, histórico e resultados de avaliações."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from apps.ahp.engine import AHPError, SAATY_SCALE
from apps.ahp.services import EvaluationAHPService
from apps.audit.services import log_action
from apps.criteria.models import Criterion
from apps.evaluations.comparisons import (
    upsert_criterion_comparison,
    upsert_supplier_comparison,
)
from apps.evaluations.forms import ProposalAttachmentForm
from apps.evaluations.models import (
    Evaluation,
    EvaluationCriterion,
    EvaluationSupplier,
    PairwiseComparison,
    ProposalAttachment,
)
from apps.services.models import EngineeringService
from apps.suppliers.models import Supplier


WIZARD_STEPS = [
    (1, "Serviço"),
    (2, "Fornecedores"),
    (3, "Critérios"),
    (4, "Comparações"),
    (5, "Consistência"),
    (6, "Resultados"),
    (7, "Relatório"),
]


def _owned_evaluation(request, pk) -> Evaluation:
    evaluation = get_object_or_404(Evaluation.objects.select_related("service", "evaluator"), pk=pk)
    if not request.user.is_administrator and evaluation.evaluator_id != request.user.id:
        raise PermissionDenied("Não tem permissão para esta avaliação.")
    return evaluation


class EvaluationListView(LoginRequiredMixin, ListView):
    model = Evaluation
    template_name = "evaluations/list.html"
    context_object_name = "evaluations"
    paginate_by = 10

    def get_queryset(self):
        qs = Evaluation.objects.select_related("service", "evaluator")
        if not self.request.user.is_administrator:
            qs = qs.filter(evaluator=self.request.user)
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        if q:
            qs = qs.filter(
                Q(service__name__icontains=q)
                | Q(objective__icontains=q)
                | Q(evaluator__username__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["statuses"] = Evaluation.Status.choices
        return ctx


class HistoryListView(EvaluationListView):
    template_name = "evaluations/history.html"

    def get_queryset(self):
        return super().get_queryset().filter(status=Evaluation.Status.COMPLETED)


class EvaluationCreateView(LoginRequiredMixin, View):
    def get(self, request):
        services = EngineeringService.objects.exclude(status=EngineeringService.Status.CANCELLED)
        return render(
            request,
            "evaluations/wizard_service.html",
            {
                "services": services,
                "steps": WIZARD_STEPS,
                "current_step": 1,
                "preselect": request.GET.get("service"),
            },
        )

    def post(self, request):
        service_id = request.POST.get("service")
        service = get_object_or_404(EngineeringService, pk=service_id)
        evaluation = Evaluation.objects.create(
            service=service,
            evaluator=request.user,
            objective="Selecionar o melhor fornecedor para o serviço de engenharia",
            status=Evaluation.Status.DRAFT,
            current_step=2,
        )
        log_action(
            user=request.user,
            action="criar_avaliacao",
            description=f"Utilizador criou avaliação para {service.name}",
            object_type="Evaluation",
            object_id=evaluation.pk,
            request=request,
        )
        return redirect("evaluations:suppliers", pk=evaluation.pk)


class EvaluationSuppliersView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        selected = set(
            evaluation.evaluation_suppliers.values_list("supplier_id", flat=True)
        )
        return render(
            request,
            "evaluations/wizard_suppliers.html",
            {
                "evaluation": evaluation,
                "suppliers": Supplier.objects.filter(status=Supplier.Status.ACTIVE),
                "selected": selected,
                "steps": WIZARD_STEPS,
                "current_step": 2,
            },
        )

    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if evaluation.is_locked:
            messages.error(request, "Avaliação bloqueada.")
            return redirect("evaluations:detail", pk=pk)
        ids = request.POST.getlist("suppliers")
        if len(ids) < 2:
            messages.error(request, "Selecione pelo menos dois fornecedores.")
            return redirect("evaluations:suppliers", pk=pk)
        evaluation.evaluation_suppliers.all().delete()
        for supplier in Supplier.objects.filter(pk__in=ids, status=Supplier.Status.ACTIVE):
            EvaluationSupplier.objects.create(
                evaluation=evaluation,
                supplier=supplier,
                snapshot_name=supplier.name,
            )
        evaluation.current_step = 3
        evaluation.save(update_fields=["current_step", "updated_at"])
        return redirect("evaluations:criteria", pk=pk)


class EvaluationCriteriaView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        selected = set(
            evaluation.evaluation_criteria.values_list("criterion_id", flat=True)
        )
        roots = Criterion.objects.filter(
            parent__isnull=True, is_active=True
        ).prefetch_related("children")
        return render(
            request,
            "evaluations/wizard_criteria.html",
            {
                "evaluation": evaluation,
                "roots": roots,
                "selected": selected,
                "steps": WIZARD_STEPS,
                "current_step": 3,
            },
        )

    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if evaluation.is_locked:
            return redirect("evaluations:detail", pk=pk)
        ids = [int(x) for x in request.POST.getlist("criteria")]
        if len(ids) < 2:
            messages.error(request, "Selecione pelo menos dois critérios.")
            return redirect("evaluations:criteria", pk=pk)
        evaluation.evaluation_criteria.all().delete()
        criteria = {c.id: c for c in Criterion.objects.filter(pk__in=ids, is_active=True)}
        created = {}
        for cid in ids:
            criterion = criteria.get(cid)
            if criterion and criterion.parent_id is None:
                created[cid] = EvaluationCriterion.objects.create(
                    evaluation=evaluation,
                    criterion=criterion,
                    parent=None,
                    snapshot_code=criterion.code,
                    snapshot_name=criterion.name,
                )
        for cid in ids:
            criterion = criteria.get(cid)
            if criterion and criterion.parent_id:
                parent_eval = created.get(criterion.parent_id)
                if parent_eval is None:
                    parent = criterion.parent
                    parent_eval = EvaluationCriterion.objects.create(
                        evaluation=evaluation,
                        criterion=parent,
                        parent=None,
                        snapshot_code=parent.code,
                        snapshot_name=parent.name,
                    )
                    created[parent.id] = parent_eval
                EvaluationCriterion.objects.create(
                    evaluation=evaluation,
                    criterion=criterion,
                    parent=parent_eval,
                    snapshot_code=criterion.code,
                    snapshot_name=criterion.name,
                )
        tops = evaluation.evaluation_criteria.filter(parent__isnull=True).count()
        if tops < 2:
            messages.error(request, "Selecione pelo menos dois critérios principais.")
            return redirect("evaluations:criteria", pk=pk)
        evaluation.status = Evaluation.Status.IN_PROGRESS
        evaluation.current_step = 4
        evaluation.save(update_fields=["status", "current_step", "updated_at"])
        return redirect("evaluations:compare", pk=pk)


def _comparison_context(evaluation, service: EvaluationAHPService, review: str = ""):
    # O modo de revisão reabre uma matriz já completa; sem ele o assistente
    # encontra sequencialmente a próxima matriz ainda incompleta.
    if review == "criteria":
        return {
            "mode": "CRITERIA", "title": "Rever comparação dos critérios",
            "parent": None, "pairs": service.required_pairs(service.top_criteria()),
            "kind": "criterion", "review": review,
        }
    if review.startswith("sub-"):
        parent = next((item for item in service.top_criteria() if str(item.pk) == review[4:]), None)
        if parent:
            return {
                "mode": "SUBCRITERIA", "title": f"Rever subcritérios de {parent.label}",
                "parent": parent, "pairs": service.required_pairs(list(parent.children.order_by("snapshot_code"))),
                "kind": "criterion", "review": review,
            }
    if review.startswith("alternatives-"):
        leaf = next((item for item in service.leaves() if str(item.pk) == review[13:]), None)
        if leaf:
            return {
                "mode": "ALTERNATIVES", "title": f"Rever fornecedores em {leaf.label}",
                "parent": leaf, "pairs": service.required_pairs(service.suppliers()),
                "kind": "supplier", "review": review,
            }
    """Determina a matriz atual a preencher (critérios → sub → alternativas)."""
    if service.missing_criterion_pairs() or not service._comparisons(
        PairwiseComparison.MatrixType.CRITERIA
    ).exists():
        pairs = service.required_pairs(service.top_criteria())
        existing = {
            tuple(sorted((c.left_criterion_id, c.right_criterion_id))): c
            for c in service._comparisons(PairwiseComparison.MatrixType.CRITERIA)
        }
        return {
            "mode": "CRITERIA",
            "title": "Qual critério é mais importante para esta decisão?",
            "parent": None,
            "pairs": pairs,
            "existing": existing,
            "kind": "criterion",
        }
    for parent in service.top_criteria():
        children = list(parent.children.order_by("snapshot_code"))
        if len(children) >= 2:
            missing = service.missing_subcriterion_pairs(parent)
            stored = service._comparisons(
                PairwiseComparison.MatrixType.SUBCRITERIA, parent
            )
            if missing or stored.count() < len(service.required_pairs(children)):
                existing = {
                    tuple(sorted((c.left_criterion_id, c.right_criterion_id))): c
                    for c in stored
                }
                return {
                    "mode": "SUBCRITERIA",
                    "title": f"Qual subcritério de «{parent.label}» é mais importante?",
                    "parent": parent,
                    "pairs": service.required_pairs(children),
                    "existing": existing,
                    "kind": "criterion",
                }
    for leaf in service.leaves():
        missing = service.missing_alternative_pairs(leaf)
        stored = service._comparisons(PairwiseComparison.MatrixType.ALTERNATIVES, leaf)
        suppliers = service.suppliers()
        needed = service.required_pairs(suppliers)
        if missing or stored.count() < len(needed):
            existing = {
                tuple(sorted((c.left_supplier_id, c.right_supplier_id))): c
                for c in stored
            }
            return {
                "mode": "ALTERNATIVES",
                "title": f"Qual fornecedor é preferível em «{leaf.label}»?",
                "parent": leaf,
                "pairs": needed,
                "existing": existing,
                "kind": "supplier",
            }
    return {"mode": "DONE", "pairs": []}


class EvaluationCompareView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        service = EvaluationAHPService(evaluation)
        context = _comparison_context(evaluation, service, request.GET.get("review", ""))
        if context["mode"] == "DONE":
            return redirect("evaluations:consistency", pk=pk)
        return render(
            request,
            "evaluations/wizard_compare.html",
            {
                "evaluation": evaluation,
                "steps": WIZARD_STEPS,
                "current_step": 4,
                "saaty": SAATY_SCALE,
                **context,
            },
        )

    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if evaluation.is_locked:
            return redirect("evaluations:detail", pk=pk)
        service = EvaluationAHPService(evaluation)
        review = request.POST.get("review", request.GET.get("review", ""))
        context = _comparison_context(evaluation, service, review)
        if context["mode"] == "DONE":
            return redirect("evaluations:consistency", pk=pk)
        parent = context.get("parent")
        for left, right in context["pairs"]:
            prefix = f"pair_{left.id}_{right.id}"
            preferred = request.POST.get(f"{prefix}_preferred")
            intensity = request.POST.get(f"{prefix}_intensity", "1")
            if not preferred:
                messages.error(request, "Complete todas as comparações.")
                return redirect("evaluations:compare", pk=pk)
            if context["kind"] == "criterion":
                matrix_type = (
                    PairwiseComparison.MatrixType.CRITERIA
                    if context["mode"] == "CRITERIA"
                    else PairwiseComparison.MatrixType.SUBCRITERIA
                )
                upsert_criterion_comparison(
                    evaluation=evaluation,
                    matrix_type=matrix_type,
                    left=left,
                    right=right,
                    preferred=preferred,
                    intensity=int(intensity),
                    parent=parent,
                )
            else:
                upsert_supplier_comparison(
                    evaluation=evaluation,
                    leaf=parent,
                    left=left,
                    right=right,
                    preferred=preferred,
                    intensity=int(intensity),
                )
        if review:
            try:
                result = service.compute()
            except AHPError as exc:
                messages.error(request, f"Não foi possível recalcular a consistência: {exc}")
                return redirect("evaluations:compare", pk=pk)
            if not result.all_consistent:
                messages.warning(
                    request,
                    "Comparações guardadas, mas ainda existe uma matriz inconsistente. Reveja as linhas marcadas a vermelho.",
                )
            messages.success(request, "Comparações revistas. A consistência foi recalculada.")
            return redirect("evaluations:consistency", pk=pk)
        return redirect("evaluations:compare", pk=pk)


class EvaluationConsistencyView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        service = EvaluationAHPService(evaluation)
        if not service.all_comparisons_complete():
            messages.warning(request, "Ainda existem comparações por preencher.")
            return redirect("evaluations:compare", pk=pk)
        try:
            service.compute()
        except AHPError as exc:
            messages.error(request, str(exc))
            return redirect("evaluations:compare", pk=pk)
        evaluation.refresh_from_db()
        matrices = evaluation.matrices.all()
        return render(
            request,
            "evaluations/wizard_consistency.html",
            {
                "evaluation": evaluation,
                "matrices": matrices,
                "result": getattr(evaluation, "ahp_result", None),
                "steps": WIZARD_STEPS,
                "current_step": 5,
                "threshold": getattr(settings, "AHP_CONSISTENCY_THRESHOLD", 0.10),
            },
        )


class EvaluationResultsView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if not hasattr(evaluation, "ahp_result"):
            return redirect("evaluations:consistency", pk=pk)
        evaluation.current_step = 6
        evaluation.save(update_fields=["current_step", "updated_at"])
        return render(
            request,
            "evaluations/results.html",
            {
                "evaluation": evaluation,
                "result": evaluation.ahp_result,
                "rankings": evaluation.rankings.select_related("evaluation_supplier"),
                "weights": evaluation.criterion_weights.select_related(
                    "evaluation_criterion"
                ),
                "matrices": evaluation.matrices.select_related("parent_criterion"),
                "priorities": evaluation.alternative_priorities.select_related(
                    "evaluation_supplier", "evaluation_criterion"
                ),
                "steps": WIZARD_STEPS,
                "current_step": 6,
            },
        )


class EvaluationCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        result = getattr(evaluation, "ahp_result", None)
        if result is None:
            messages.error(request, "Calcule os resultados antes de concluir.")
            return redirect("evaluations:consistency", pk=pk)
        if not result.all_consistent:
            allow = getattr(settings, "AHP_ALLOW_ADMIN_OVERRIDE_INCONSISTENCY", True)
            if not (allow and request.user.is_administrator and request.POST.get("override")):
                messages.error(
                    request,
                    "Não é possível concluir uma avaliação inconsistente. Revise as comparações.",
                )
                return redirect("evaluations:consistency", pk=pk)
            evaluation.allow_inconsistent_completion = True
        evaluation.status = Evaluation.Status.COMPLETED
        evaluation.completed_at = timezone.now()
        evaluation.current_step = 7
        evaluation.save()
        log_action(
            user=request.user,
            action="concluir_avaliacao",
            description=f"Utilizador concluiu a avaliação #{evaluation.pk}",
            object_type="Evaluation",
            object_id=evaluation.pk,
            request=request,
        )
        messages.success(request, "Avaliação concluída e registada no histórico.")
        return redirect("evaluations:detail", pk=pk)


class EvaluationCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if evaluation.status == Evaluation.Status.COMPLETED:
            messages.error(request, "Uma avaliação concluída não pode ser cancelada.")
            return redirect("evaluations:detail", pk=pk)
        evaluation.status = Evaluation.Status.CANCELLED
        evaluation.save(update_fields=["status", "updated_at"])
        log_action(
            user=request.user,
            action="cancelar_avaliacao",
            description=f"Utilizador cancelou a avaliação #{evaluation.pk}",
            object_type="Evaluation",
            object_id=evaluation.pk,
            request=request,
        )
        return redirect("evaluations:list")


class EvaluationDetailView(LoginRequiredMixin, DetailView):
    model = Evaluation
    template_name = "evaluations/detail.html"
    context_object_name = "evaluation"

    def get_queryset(self):
        qs = Evaluation.objects.select_related("service", "evaluator", "ahp_result")
        if not self.request.user.is_administrator:
            qs = qs.filter(evaluator=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        evaluation = self.object
        ctx["rankings"] = evaluation.rankings.select_related("evaluation_supplier")
        ctx["weights"] = evaluation.criterion_weights.select_related("evaluation_criterion")
        ctx["matrices"] = evaluation.matrices.select_related("parent_criterion")
        ctx["steps"] = WIZARD_STEPS
        ctx["current_step"] = 7 if evaluation.status == Evaluation.Status.COMPLETED else evaluation.current_step
        return ctx


class EvaluationAttachmentsView(LoginRequiredMixin, View):
    """Permite anexar e consultar propostas ligadas à avaliação."""

    template_name = "evaluations/attachments.html"

    def get(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        form = ProposalAttachmentForm()
        form.fields["evaluation_supplier"].queryset = evaluation.evaluation_suppliers.all()
        return render(
            request,
            self.template_name,
            {
                "evaluation": evaluation,
                "form": form,
                "attachments": ProposalAttachment.objects.filter(
                    evaluation_supplier__evaluation=evaluation
                ).select_related("evaluation_supplier", "uploaded_by"),
            },
        )

    def post(self, request, pk):
        evaluation = _owned_evaluation(request, pk)
        if evaluation.is_locked:
            messages.error(request, "Não é possível alterar anexos de uma avaliação bloqueada.")
            return redirect("evaluations:attachments", pk=pk)
        form = ProposalAttachmentForm(request.POST, request.FILES)
        form.fields["evaluation_supplier"].queryset = evaluation.evaluation_suppliers.all()
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.uploaded_by = request.user
            attachment.save()
            log_action(
                user=request.user,
                action="anexar_proposta",
                description=f"Utilizador anexou proposta para {attachment.evaluation_supplier.snapshot_name}",
                object_type="ProposalAttachment",
                object_id=attachment.pk,
                request=request,
            )
            messages.success(request, "Proposta anexada com sucesso.")
            return redirect("evaluations:attachments", pk=pk)
        attachments = ProposalAttachment.objects.filter(
            evaluation_supplier__evaluation=evaluation
        ).select_related("evaluation_supplier", "uploaded_by")
        return render(request, self.template_name, {"evaluation": evaluation, "form": form, "attachments": attachments})


class EvaluationMatrixJsonView(LoginRequiredMixin, View):
    def get(self, request, pk, matrix_id):
        evaluation = _owned_evaluation(request, pk)
        matrix = get_object_or_404(evaluation.matrices, pk=matrix_id)
        return JsonResponse(
            {
                "labels": matrix.labels,
                "matrix": matrix.matrix,
                "normalized": matrix.normalized_matrix,
                "cr": str(matrix.cr),
            }
        )
