from django.urls import path

from apps.evaluations import views

app_name = "evaluations"

urlpatterns = [
    path("", views.EvaluationListView.as_view(), name="list"),
    path("historico/", views.HistoryListView.as_view(), name="history"),
    path("nova/", views.EvaluationCreateView.as_view(), name="create"),
    path("<int:pk>/", views.EvaluationDetailView.as_view(), name="detail"),
    path("<int:pk>/anexos/", views.EvaluationAttachmentsView.as_view(), name="attachments"),
    path("<int:pk>/fornecedores/", views.EvaluationSuppliersView.as_view(), name="suppliers"),
    path("<int:pk>/criterios/", views.EvaluationCriteriaView.as_view(), name="criteria"),
    path("<int:pk>/comparar/", views.EvaluationCompareView.as_view(), name="compare"),
    path("<int:pk>/consistencia/", views.EvaluationConsistencyView.as_view(), name="consistency"),
    path("<int:pk>/resultados/", views.EvaluationResultsView.as_view(), name="results"),
    path("<int:pk>/concluir/", views.EvaluationCompleteView.as_view(), name="complete"),
    path("<int:pk>/cancelar/", views.EvaluationCancelView.as_view(), name="cancel"),
    path("<int:pk>/matriz/<int:matrix_id>.json", views.EvaluationMatrixJsonView.as_view(), name="matrix_json"),
]
