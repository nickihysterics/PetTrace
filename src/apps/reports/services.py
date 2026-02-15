from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.billing.models import Invoice, Payment, PaymentAdjustment
from apps.inventory.models import InventoryItem, StockMovement
from apps.labs.models import LabOrder
from apps.users.access import restrict_queryset_for_user_scope
from apps.visits.models import Appointment


def _to_decimal_str(value) -> str:
    return str(value if value is not None else Decimal("0"))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    values_sorted = sorted(values)
    size = len(values_sorted)
    middle = size // 2
    if size % 2 == 1:
        return round(values_sorted[middle], 2)
    return round((values_sorted[middle - 1] + values_sorted[middle]) / 2, 2)


def _period_payload(*, date_from: date, date_to: date) -> dict:
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "generated_at": timezone.now().isoformat(),
    }


def build_lab_turnaround_payload(*, date_from: date, date_to: date, start_dt, end_dt, user=None) -> dict:
    orders = LabOrder.objects.filter(ordered_at__gte=start_dt, ordered_at__lt=end_dt)
    if user is not None:
        orders = restrict_queryset_for_user_scope(
            queryset=orders,
            user=user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
    total_orders = orders.count()
    done_orders = orders.filter(status=LabOrder.LabOrderStatus.DONE).count()

    status_breakdown = list(
        orders.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    turnaround_values: list[float] = []
    sla_breached_done = 0
    done_orders_qs = orders.filter(completed_at__isnull=False).values_list(
        "ordered_at",
        "completed_at",
        "sla_minutes",
    )
    for ordered_at, completed_at, sla_minutes in done_orders_qs:
        turnaround_minutes = (completed_at - ordered_at).total_seconds() / 60
        turnaround_values.append(turnaround_minutes)
        if turnaround_minutes > sla_minutes:
            sla_breached_done += 1

    pending_statuses = [
        LabOrder.LabOrderStatus.PLANNED,
        LabOrder.LabOrderStatus.COLLECTED,
        LabOrder.LabOrderStatus.IN_TRANSPORT,
        LabOrder.LabOrderStatus.RECEIVED,
        LabOrder.LabOrderStatus.IN_PROCESS,
    ]
    now = timezone.now()
    sla_breached_pending = 0
    pending_orders_qs = orders.filter(status__in=pending_statuses).values_list(
        "ordered_at",
        "sla_minutes",
    )
    for ordered_at, sla_minutes in pending_orders_qs:
        if ((now - ordered_at).total_seconds() / 60) > sla_minutes:
            sla_breached_pending += 1

    avg_turnaround = (
        round(sum(turnaround_values) / len(turnaround_values), 2)
        if turnaround_values
        else None
    )
    median_turnaround = _median(turnaround_values)

    return {
        **_period_payload(date_from=date_from, date_to=date_to),
        "total_orders": total_orders,
        "done_orders": done_orders,
        "status_breakdown": status_breakdown,
        "avg_turnaround_minutes": avg_turnaround,
        "median_turnaround_minutes": median_turnaround,
        "sla_breached_done": sla_breached_done,
        "sla_breached_pending": sla_breached_pending,
    }


def build_tube_usage_payload(*, date_from: date, date_to: date, start_dt, end_dt, user=None) -> dict:
    usage_movements = StockMovement.objects.filter(
        movement_type=StockMovement.MovementType.WRITE_OFF,
        reference_type="specimen_tube",
        created_at__gte=start_dt,
        created_at__lt=end_dt,
    )

    usage_by_item = list(
        usage_movements.values("item__id", "item__sku", "item__name")
        .annotate(total_quantity=Sum("quantity"), movements=Count("id"))
        .order_by("-total_quantity")
    )

    low_stock_items = []
    for item in InventoryItem.objects.filter(is_active=True).prefetch_related("batches"):
        available = sum(
            (batch.quantity_available for batch in item.batches.all()),
            Decimal("0"),
        )
        if available <= item.min_stock:
            low_stock_items.append(
                {
                    "item_id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "available_stock": _to_decimal_str(available),
                    "min_stock": _to_decimal_str(item.min_stock),
                }
            )

    total_written_off = usage_movements.aggregate(total=Sum("quantity"))["total"] or Decimal("0")

    return {
        **_period_payload(date_from=date_from, date_to=date_to),
        "total_movements": usage_movements.count(),
        "total_written_off": _to_decimal_str(total_written_off),
        "usage_by_item": usage_by_item,
        "low_stock_items": low_stock_items,
    }


def build_appointment_ops_payload(*, date_from: date, date_to: date, start_dt, end_dt, user=None) -> dict:
    appointments = Appointment.objects.select_related("visit").filter(
        start_at__gte=start_dt,
        start_at__lt=end_dt,
    )
    if user is not None:
        appointments = restrict_queryset_for_user_scope(
            queryset=appointments,
            user=user,
            branch_field="branch",
            cabinet_field="cabinet",
        )
    total_appointments = appointments.count()
    no_show_count = appointments.filter(status=Appointment.AppointmentStatus.NO_SHOW).count()
    linked_visits_count = appointments.filter(visit__isnull=False).count()

    status_breakdown = list(
        appointments.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    checkin_to_start_values: list[float] = []
    checkin_pairs_qs = appointments.filter(
        checked_in_at__isnull=False,
        visit__started_at__isnull=False,
    ).values_list("checked_in_at", "visit__started_at")
    for checked_in_at, visit_started_at in checkin_pairs_qs:
        minutes = (visit_started_at - checked_in_at).total_seconds() / 60
        if minutes >= 0:
            checkin_to_start_values.append(minutes)

    avg_checkin_to_start = (
        round(sum(checkin_to_start_values) / len(checkin_to_start_values), 2)
        if checkin_to_start_values
        else None
    )

    queue_stats = appointments.exclude(queue_number__isnull=True).aggregate(
        avg_queue=Avg("queue_number")
    )
    no_show_rate = (
        round((no_show_count * 100 / total_appointments), 2)
        if total_appointments
        else 0
    )
    avg_queue_number = (
        round(queue_stats["avg_queue"], 2)
        if queue_stats["avg_queue"] is not None
        else None
    )

    return {
        **_period_payload(date_from=date_from, date_to=date_to),
        "total_appointments": total_appointments,
        "linked_visits_count": linked_visits_count,
        "no_show_count": no_show_count,
        "no_show_rate_percent": no_show_rate,
        "status_breakdown": status_breakdown,
        "avg_checkin_to_start_minutes": avg_checkin_to_start,
        "avg_queue_number": avg_queue_number,
    }


def build_finance_summary_payload(*, date_from: date, date_to: date, start_dt, end_dt, user=None) -> dict:
    invoices = Invoice.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    payments = Payment.objects.filter(paid_at__gte=start_dt, paid_at__lt=end_dt)
    adjustments = PaymentAdjustment.objects.filter(adjusted_at__gte=start_dt, adjusted_at__lt=end_dt)
    if user is not None:
        invoices = restrict_queryset_for_user_scope(
            queryset=invoices,
            user=user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
        payments = restrict_queryset_for_user_scope(
            queryset=payments,
            user=user,
            branch_field="invoice__visit__branch",
            cabinet_field="invoice__visit__cabinet",
        )
        adjustments = restrict_queryset_for_user_scope(
            queryset=adjustments,
            user=user,
            branch_field="payment__invoice__visit__branch",
            cabinet_field="payment__invoice__visit__cabinet",
        )

    issued_amount = invoices.filter(
        status__in=[
            Invoice.InvoiceStatus.FORMED,
            Invoice.InvoiceStatus.POSTED,
            Invoice.InvoiceStatus.PAID,
        ]
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    paid_amount = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    refund_amount = adjustments.filter(
        adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    correction_amount = adjustments.filter(
        adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    net_paid_amount = paid_amount - refund_amount + correction_amount

    outstanding_amount = Decimal("0")
    issued_invoices = invoices.filter(
        status__in=[Invoice.InvoiceStatus.FORMED, Invoice.InvoiceStatus.POSTED]
    )
    issued_invoice_ids = list(issued_invoices.values_list("id", flat=True))

    invoice_payments = {
        row["invoice_id"]: row["total"] or Decimal("0")
        for row in Payment.objects.filter(invoice_id__in=issued_invoice_ids)
        .values("invoice_id")
        .annotate(total=Sum("amount"))
    }

    invoice_refunds: dict[int, Decimal] = {}
    invoice_corrections: dict[int, Decimal] = {}
    for row in PaymentAdjustment.objects.filter(payment__invoice_id__in=issued_invoice_ids).values(
        "payment__invoice_id",
        "adjustment_type",
    ).annotate(total=Sum("amount")):
        invoice_id = row["payment__invoice_id"]
        total = row["total"] or Decimal("0")
        if row["adjustment_type"] == PaymentAdjustment.AdjustmentType.REFUND:
            invoice_refunds[invoice_id] = total
        elif row["adjustment_type"] == PaymentAdjustment.AdjustmentType.CORRECTION:
            invoice_corrections[invoice_id] = total

    for invoice in issued_invoices:
        paid_total = invoice_payments.get(invoice.id, Decimal("0"))
        paid_total -= invoice_refunds.get(invoice.id, Decimal("0"))
        paid_total += invoice_corrections.get(invoice.id, Decimal("0"))
        remainder = invoice.total_amount - paid_total
        if remainder > 0:
            outstanding_amount += remainder

    payment_method_breakdown = list(
        payments.values("method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("method")
    )

    avg_invoice_amount = _to_decimal_str(invoices.aggregate(avg=Avg("total_amount"))["avg"])

    return {
        **_period_payload(date_from=date_from, date_to=date_to),
        "invoice_count": invoices.count(),
        "payment_count": payments.count(),
        "issued_amount": _to_decimal_str(issued_amount),
        "paid_amount": _to_decimal_str(paid_amount),
        "refund_amount": _to_decimal_str(refund_amount),
        "correction_amount": _to_decimal_str(correction_amount),
        "net_paid_amount": _to_decimal_str(net_paid_amount),
        "outstanding_amount": _to_decimal_str(outstanding_amount),
        "avg_invoice_amount": avg_invoice_amount,
        "payment_method_breakdown": payment_method_breakdown,
    }
