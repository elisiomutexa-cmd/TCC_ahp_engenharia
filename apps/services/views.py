from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit.services import log_action
from apps.services.forms import EngineeringServiceForm
from apps.services.models import EngineeringService


class ServiceListView(LoginRequiredMixin, ListView):
    model = EngineeringService
    template_name = "services/list.html"
    context_object_name = "services"
    paginate_by = 10

    def get_queryset(self):
        qs = EngineeringService.objects.all()
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        service_type = self.request.GET.get("type", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(location__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if service_type:
            qs = qs.filter(service_type=service_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["type"] = self.request.GET.get("type", "")
        ctx["types"] = EngineeringService.ServiceType.choices
        return ctx


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = EngineeringService
    form_class = EngineeringServiceForm
    template_name = "services/form.html"
    success_url = reverse_lazy("services:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="criar_servico",
            description=f"Utilizador criou o serviço {self.object.name}",
            object_type="EngineeringService",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = EngineeringService
    form_class = EngineeringServiceForm
    template_name = "services/form.html"
    success_url = reverse_lazy("services:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="alterar_servico",
            description=f"Utilizador alterou o serviço {self.object.name}",
            object_type="EngineeringService",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class ServiceDetailView(LoginRequiredMixin, DetailView):
    model = EngineeringService
    template_name = "services/detail.html"
    context_object_name = "service"
