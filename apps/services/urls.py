from django.urls import path

from apps.services import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("novo/", views.ServiceCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ServiceDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.ServiceUpdateView.as_view(), name="update"),
]
