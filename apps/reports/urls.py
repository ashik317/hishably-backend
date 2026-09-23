from django.urls import path

from .views import AgingReportView, DashboardView, RepPerformanceView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reports/aging/", AgingReportView.as_view(), name="report-aging"),
    path("reports/reps/", RepPerformanceView.as_view(), name="report-reps"),
]
