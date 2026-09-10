from django.urls import path

from apps.suppliers import views

app_name = "suppliers"

urlpatterns = [
    path("", views.SupplierListView.as_view(), name="list"),
    path("novo/", views.SupplierCreateView.as_view(), name="create"),
    path("<int:pk>/", views.SupplierDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.SupplierUpdateView.as_view(), name="update"),
    path("<int:pk>/desativar/", views.SupplierDeactivateView.as_view(), name="deactivate"),
]
