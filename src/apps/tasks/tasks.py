from celery import shared_task
from django.utils import timezone

from .models import Notification, Task


@shared_task
def mark_overdue_tasks() -> int:
    now = timezone.now()
    updated = Task.objects.filter(
        due_at__lt=now,
        status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS],
    ).exclude(priority=Task.Priority.URGENT).update(priority=Task.Priority.URGENT)
    return updated


@shared_task
def send_pending_notifications() -> int:
    sent = 0
    for notification in Notification.objects.filter(status=Notification.DeliveryStatus.PENDING)[:100]:
        notification.mark_sent()
        sent += 1
    return sent
