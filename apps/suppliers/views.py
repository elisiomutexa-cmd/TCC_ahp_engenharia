from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit.services import log_action
from apps.suppliers.forms import SupplierForm
from apps.suppliers.models import Supplier


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = "suppliers/list.html"
    context_object_name = "suppliers"
    paginate_by = 10

    def get_queryset(self):
        qs = Supplier.objects.all()
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        province = self.request.GET.get("province", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(nuit__icontains=q)
                | Q(email__icontains=q)
                | Q(city__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if province:
            qs = qs.filter(province__icontains=province)
        ordering = self.request.GET.get("o", "name")
        allowed = {"name", "-name", "created_at", "-created_at", "city"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["province"] = self.request.GET.get("province", "")
        return ctx


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/form.html"
    success_url = reverse_lazy("suppliers:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="criar_fornecedor",
            description=f"Utilizador criou o fornecedor {self.object.name}",
            object_type="Supplier",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/form.html"
    success_url = reverse_lazy("suppliers:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action="alterar_fornecedor",
            description=f"Utilizador alterou o fornecedor {self.object.name}",
            object_type="Supplier",
            object_id=self.object.pk,
            request=self.request,
        )
        return response


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = "suppliers/detail.html"
    context_object_name = "supplier"


class SupplierDeactivateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    fields = []
    success_url = reverse_lazy("suppliers:list")

    def form_valid(self, form):
        self.object.status = Supplier.Status.INACTIVE
        self.object.save(update_fields=["status", "updated_at"])
        log_action(
            user=self.request.user,
            action="desativar_fornecedor",
            description=f"Utilizador desativou o fornecedor {self.object.name}",
            object_type="Supplier",
            object_id=self.object.pk,
            request=self.request,
        )
        from django.shortcuts import redirect

        return redirect(self.success_url)
