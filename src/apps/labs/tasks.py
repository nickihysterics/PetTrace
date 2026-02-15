from celery import shared_task
from django.utils import timezone

from apps.common.services import get_setting_int
from apps.tasks.models import Notification

from .models import LabOrder


@shared_task
def check_lab_order_sla() -> int:
    now = timezone.now()
    pending_statuses = [
        LabOrder.LabOrderStatus.PLANNED,
        LabOrder.LabOrderStatus.COLLECTED,
        LabOrder.LabOrderStatus.IN_TRANSPORT,
        LabOrder.LabOrderStatus.RECEIVED,
        LabOrder.LabOrderStatus.IN_PROCESS,
    ]

    breached = 0
    default_sla_minutes = get_setting_int("labs.sla_overdue_minutes", default=15)
    for order in LabOrder.objects.filter(status__in=pending_statuses):
        elapsed_minutes = (now - order.ordered_at).total_seconds() / 60
        effective_sla = order.sla_minutes or default_sla_minutes
        if elapsed_minutes <= effective_sla:
            continue

        breached += 1
        veterinarian = order.visit.veterinarian
        if veterinarian is None:
            continue

        exists = Notification.objects.filter(
            recipient=veterinarian,
            payload__lab_order_id=order.id,
            payload__event="lab_order_sla_breach",
            status=Notification.DeliveryStatus.PENDING,
        ).exists()
        if exists:
            continue

        Notification.objects.create(
            recipient=veterinarian,
            channel=Notification.Channel.IN_APP,
            title="Нарушение SLA лабораторного заказа",
            body=f"Заказ #{order.id} превысил SLA ({effective_sla} мин).",
            payload={
                "event": "lab_order_sla_breach",
                "lab_order_id": order.id,
                "elapsed_minutes": round(elapsed_minutes, 2),
            },
            status=Notification.DeliveryStatus.PENDING,
        )
    return breached
