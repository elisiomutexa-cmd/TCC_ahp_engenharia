"""Mixins de autorização por papel."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdministratorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_administrator

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Acesso restrito a administradores.")
        return super().handle_no_permission()


class StaffOrOwnerMixin(LoginRequiredMixin):
    """Administrador vê tudo; gestor só os seus objetos com campo evaluator."""

    def filter_queryset(self, qs):
        user = self.request.user
        if user.is_administrator:
            return qs
        return qs.filter(evaluator=user)
