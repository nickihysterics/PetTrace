from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import permissions, response, status
from rest_framework.views import APIView

from .cache import get_or_set_report_payload
from .export import csv_export_response
from .serializers import (
    AppointmentOpsReportSerializer,
    FinanceSummaryReportSerializer,
    LabTurnaroundReportSerializer,
    TubeUsageReportSerializer,
)
from .services import (
    build_appointment_ops_payload,
    build_finance_summary_payload,
    build_lab_turnaround_payload,
    build_tube_usage_payload,
)

REPORT_COMMON_PARAMETERS = [
    OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        "export",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description="Укажите 'csv', чтобы получить выгрузку в формате CSV.",
    ),
    OpenApiParameter(
        "refresh",
        OpenApiTypes.BOOL,
        OpenApiParameter.QUERY,
        required=False,
        description="Укажите true, чтобы выполнить запрос без использования кеша.",
    ),
]


def _parse_boundary_date(raw_value: str | None, field_name: str):
    if not raw_value:
        return None
    parsed_datetime = parse_datetime(raw_value)
    if parsed_datetime is not None:
        if timezone.is_naive(parsed_datetime):
            parsed_datetime = timezone.make_aware(parsed_datetime)
        return timezone.localtime(parsed_datetime).date()
    parsed_date = parse_date(raw_value)
    if parsed_date is not None:
        return parsed_date
    raise ValueError(f"invalid {field_name}: expected YYYY-MM-DD or ISO datetime")


class ReportPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        required_permissions = getattr(view, "required_permissions", ())
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.has_perms(required_permissions)


class BaseReportView(APIView):
    permission_classes = [ReportPermissions]
    required_permissions: tuple[str, ...] = tuple()
    cache_domains: tuple[str, ...] = tuple()
    report_name: str = "report"
    payload_builder = None

    def get_date_range(self, request, default_days: int = 30):
        today = timezone.localdate()
        date_to = _parse_boundary_date(request.query_params.get("date_to"), "date_to") or today
        date_from = _parse_boundary_date(request.query_params.get("date_from"), "date_from") or (
            date_to - timedelta(days=default_days - 1)
        )
        if date_from > date_to:
            raise ValueError("date_from cannot be greater than date_to")

        start_dt = timezone.make_aware(datetime.combine(date_from, time.min))
        end_dt = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min))
        return date_from, date_to, start_dt, end_dt

    def cache_params(self, *, date_from, date_to) -> dict:
        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        }

    def wants_csv_export(self, request) -> bool:
        return request.query_params.get("export", "").strip().lower() == "csv"

    def wants_cache_refresh(self, request) -> bool:
        return request.query_params.get("refresh", "").strip().lower() in {"1", "true", "yes"}

    def build_csv_filename(self) -> str:
        return f"{self.report_name}-{timezone.localdate().isoformat()}.csv"

    def build_payload(self, *, date_from, date_to, start_dt, end_dt) -> dict:
        if self.payload_builder is None:
            raise RuntimeError(f"payload_builder is not configured for {self.__class__.__name__}")
        return self.payload_builder(
            date_from=date_from,
            date_to=date_to,
            start_dt=start_dt,
            end_dt=end_dt,
            user=self.request.user,
        )

    def get_cached_payload(self, *, request, params: dict, builder):
        if self.wants_cache_refresh(request):
            return builder()
        return get_or_set_report_payload(
            report_name=self.report_name,
            params=params,
            domains=self.cache_domains,
            builder=builder,
        )

    def render_report(self, request, payload: dict):
        if self.wants_csv_export(request):
            return csv_export_response(payload=payload, filename=self.build_csv_filename())
        return response.Response(payload)

    def get(self, request):
        try:
            date_from, date_to, start_dt, end_dt = self.get_date_range(request)
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = self.get_cached_payload(
            request=request,
            params=self.cache_params(date_from=date_from, date_to=date_to),
            builder=lambda: self.build_payload(
                date_from=date_from,
                date_to=date_to,
                start_dt=start_dt,
                end_dt=end_dt,
            ),
        )
        return self.render_report(request, payload)


class LabTurnaroundReportView(BaseReportView):
    required_permissions = ("labs.view_laborder", "labs.view_specimen", "labs.view_labtest")
    cache_domains = ("labs",)
    report_name = "labs-turnaround"
    payload_builder = staticmethod(build_lab_turnaround_payload)

    @extend_schema(
        parameters=REPORT_COMMON_PARAMETERS,
        responses={200: LabTurnaroundReportSerializer},
    )
    def get(self, request):
        return super().get(request)


class TubeUsageReportView(BaseReportView):
    required_permissions = (
        "inventory.view_stockmovement",
        "inventory.view_inventoryitem",
        "labs.view_tube",
    )
    cache_domains = ("inventory",)
    report_name = "inventory-tube-usage"
    payload_builder = staticmethod(build_tube_usage_payload)

    @extend_schema(
        parameters=REPORT_COMMON_PARAMETERS,
        responses={200: TubeUsageReportSerializer},
    )
    def get(self, request):
        return super().get(request)


class AppointmentOpsReportView(BaseReportView):
    required_permissions = ("visits.view_appointment", "visits.view_visit")
    cache_domains = ("appointments",)
    report_name = "appointments-operations"
    payload_builder = staticmethod(build_appointment_ops_payload)

    @extend_schema(
        parameters=REPORT_COMMON_PARAMETERS,
        responses={200: AppointmentOpsReportSerializer},
    )
    def get(self, request):
        return super().get(request)


class FinanceSummaryReportView(BaseReportView):
    required_permissions = (
        "billing.view_invoice",
        "billing.view_payment",
        "billing.view_invoiceline",
    )
    cache_domains = ("finance",)
    report_name = "finance-summary"
    payload_builder = staticmethod(build_finance_summary_payload)

    @extend_schema(
        parameters=REPORT_COMMON_PARAMETERS,
        responses={200: FinanceSummaryReportSerializer},
    )
    def get(self, request):
        return super().get(request)
