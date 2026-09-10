"""Rotas principais do SAD AHP Engenharia."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "AHP Engenharia — Administração"
admin.site.site_title = "AHP Engenharia"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("contas/", include("apps.accounts.urls")),
    path("fornecedores/", include("apps.suppliers.urls")),
    path("servicos/", include("apps.services.urls")),
    path("criterios/", include("apps.criteria.urls")),
    path("avaliacoes/", include("apps.evaluations.urls")),
    path("relatorios/", include("apps.reports.urls")),
    path("", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
