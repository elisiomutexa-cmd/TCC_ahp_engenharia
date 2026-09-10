from django.urls import path

from apps.criteria import views

app_name = "criteria"

urlpatterns = [
    path("", views.CriterionListView.as_view(), name="list"),
    path("novo/", views.CriterionCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.CriterionUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.CriterionDeleteView.as_view(), name="delete"),
]
