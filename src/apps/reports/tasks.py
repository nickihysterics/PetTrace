from __future__ import annotations

from datetime import datetime, time, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .cache import get_or_set_report_payload
from .services import (
    build_appointment_ops_payload,
    build_finance_summary_payload,
    build_lab_turnaround_payload,
    build_tube_usage_payload,
)

DEFAULT_WARMUP_DAYS = (1, 7, 30)
REPORT_BUILDERS = (
    ("labs-turnaround", ("labs",), build_lab_turnaround_payload),
    ("inventory-tube-usage", ("inventory",), build_tube_usage_payload),
    ("appointments-operations", ("appointments",), build_appointment_ops_payload),
    ("finance-summary", ("finance",), build_finance_summary_payload),
)


def _parse_warmup_days(raw_days) -> tuple[int, ...]:
    if not raw_days:
        return DEFAULT_WARMUP_DAYS

    parsed: list[int] = []
    for raw in raw_days:
        try:
            day = int(raw)
        except (TypeError, ValueError):
            continue
        if day > 0:
            parsed.append(day)

    unique_days = tuple(sorted(set(parsed)))
    return unique_days or DEFAULT_WARMUP_DAYS


def _date_window_for_days(days: int):
    date_to = timezone.localdate()
    date_from = date_to - timedelta(days=days - 1)
    start_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    end_dt = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min))
    return date_from, date_to, start_dt, end_dt


def _make_payload_builder(*, builder, date_from, date_to, start_dt, end_dt):
    def _payload():
        return builder(
            date_from=date_from,
            date_to=date_to,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    return _payload


@shared_task
def warm_reports_cache() -> dict:
    days_windows = _parse_warmup_days(getattr(settings, "REPORTS_WARMUP_DAYS", DEFAULT_WARMUP_DAYS))

    entries = 0
    for days in days_windows:
        date_from, date_to, start_dt, end_dt = _date_window_for_days(days)
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        }
        for report_name, domains, builder in REPORT_BUILDERS:
            payload_builder = _make_payload_builder(
                builder=builder,
                date_from=date_from,
                date_to=date_to,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            get_or_set_report_payload(
                report_name=report_name,
                params=params,
                domains=domains,
                builder=payload_builder,
            )
            entries += 1

    return {
        "windows": list(days_windows),
        "reports": len(REPORT_BUILDERS),
        "entries": entries,
    }
