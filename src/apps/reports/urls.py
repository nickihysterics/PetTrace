from django.urls import path

from .views import (
    AppointmentOpsReportView,
    FinanceSummaryReportView,
    LabTurnaroundReportView,
    TubeUsageReportView,
)

urlpatterns = [
    path(
        "reports/labs/turnaround/",
        LabTurnaroundReportView.as_view(),
        name="report-lab-turnaround",
    ),
    path(
        "reports/inventory/tube-usage/",
        TubeUsageReportView.as_view(),
        name="report-inventory-tube-usage",
    ),
    path(
        "reports/appointments/operations/",
        AppointmentOpsReportView.as_view(),
        name="report-appointments-operations",
    ),
    path(
        "reports/finance/summary/",
        FinanceSummaryReportView.as_view(),
        name="report-finance-summary",
    ),
]
