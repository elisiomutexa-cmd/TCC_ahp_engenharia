from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.mixins import AdministratorRequiredMixin
from apps.audit.services import log_action
from apps.criteria.forms import CriterionForm
from apps.criteria.models import Criterion


class CriterionListView(AdministratorRequiredMixin, ListView):
    model = Criterion
    template_name = "criteria/list.html"
    context_object_name = "criteria"

    def get_queryset(self):
        return Criterion.objects.filter(parent__isnull=True).prefetch_related("children")


class CriterionCreateView(AdministratorRequiredMixin, CreateView):
    model = Criterion
    form_class = CriterionForm
    template_name = "criteria/form.html"
    success_url = reverse_lazy("criteria:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="criar_criterio",
            description=f"Utilizador criou o critério {self.object}",
            object_type="Criterion",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class CriterionUpdateView(AdministratorRequiredMixin, UpdateView):
    model = Criterion
    form_class = CriterionForm
    template_name = "criteria/form.html"
    success_url = reverse_lazy("criteria:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="alterar_criterio",
            description=f"Utilizador alterou o critério {self.object}",
            object_type="Criterion",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class CriterionDeleteView(AdministratorRequiredMixin, DeleteView):
    model = Criterion
    template_name = "criteria/confirm_delete.html"
    success_url = reverse_lazy("criteria:list")

    def form_valid(self, form):
        log_action(
            user=self.request.user,
            action="excluir_criterio",
            description=f"Utilizador excluiu o critério {self.object}",
            object_type="Criterion",
            object_id=self.object.pk,
            request=self.request,
        )
        messages.success(self.request, "Critério excluído.")
        return super().form_valid(form)
