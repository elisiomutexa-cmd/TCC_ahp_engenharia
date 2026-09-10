from collections import Counter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView

from apps.evaluations.models import Evaluation, Ranking
from apps.services.models import EngineeringService
from apps.suppliers.models import Supplier


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        evaluations = Evaluation.objects.all()
        if not self.request.user.is_administrator:
            evaluations = evaluations.filter(evaluator=self.request.user)

        ctx["total_suppliers"] = Supplier.objects.count()
        ctx["total_services"] = EngineeringService.objects.count()
        ctx["in_progress"] = evaluations.filter(
            status__in=[Evaluation.Status.IN_PROGRESS, Evaluation.Status.INCONSISTENT, Evaluation.Status.DRAFT]
        ).count()
        ctx["completed"] = evaluations.filter(status=Evaluation.Status.COMPLETED).count()
        ctx["decisions"] = ctx["completed"]

        top = (
            Ranking.objects.filter(is_recommended=True, evaluation__status=Evaluation.Status.COMPLETED)
            .values("evaluation_supplier__snapshot_name")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )
        ctx["top_supplier"] = (
            top["evaluation_supplier__snapshot_name"] if top else "—"
        )

        ctx["status_chart"] = list(
            evaluations.values("status").annotate(total=Count("id")).order_by("status")
        )
        ctx["service_chart"] = list(
            evaluations.values("service__name")
            .annotate(total=Count("id"))
            .order_by("-total")[:8]
        )
        # Evita CONVERT_TZ do MySQL: instalações locais normalmente não têm as
        # tabelas de fusos horários carregadas, o que faria TruncMonth retornar
        # NULL e quebraria o dashboard.
        monthly_counts = Counter()
        completed_dates = evaluations.filter(
            status=Evaluation.Status.COMPLETED,
            completed_at__isnull=False,
        ).values_list("completed_at", flat=True)
        for completed_at in completed_dates:
            local_date = timezone.localtime(completed_at)
            monthly_counts[local_date.strftime("%Y-%m")] += 1
        ctx["timeline"] = [
            {"month": month, "total": total}
            for month, total in sorted(monthly_counts.items())
        ]
        last_completed = (
            evaluations.filter(status=Evaluation.Status.COMPLETED)
            .prefetch_related("rankings__evaluation_supplier")
            .order_by("-completed_at")
            .first()
        )
        ctx["last_ranking"] = []
        ctx["last_weights"] = []
        if last_completed:
            ctx["last_ranking"] = [
                {"label": r.evaluation_supplier.snapshot_name, "percent": float(r.percent)}
                for r in last_completed.rankings.all()
            ]
            ctx["last_weights"] = [
                {
                    "label": w.evaluation_criterion.snapshot_name,
                    "weight": float(w.local_weight),
                }
                for w in last_completed.criterion_weights.filter(
                    evaluation_criterion__parent__isnull=True
                )
            ]
            ctx["last_evaluation"] = last_completed
        ctx["recent"] = evaluations.select_related("service")[:6]
        return ctx
