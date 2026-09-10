from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("<int:pk>/", views.ReportPreviewView.as_view(), name="preview"),
    path("<int:pk>/pdf/", views.ReportPDFView.as_view(), name="pdf"),
    path("<int:pk>/csv/", views.ReportCSVView.as_view(), name="csv"),
    path("<int:pk>/excel/", views.ReportExcelView.as_view(), name="excel"),
]
