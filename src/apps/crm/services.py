from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import CommunicationLog, Reminder


@transaction.atomic
def dispatch_communication(*, communication: CommunicationLog, actor=None) -> CommunicationLog:
    if communication.status in {CommunicationLog.Status.SENT, CommunicationLog.Status.CANCELED}:
        return communication

    communication.status = CommunicationLog.Status.SENT
    communication.sent_at = timezone.now()
    if actor and actor.is_authenticated:
        communication.sent_by = actor
    communication.save(update_fields=["status", "sent_at", "sent_by", "updated_at"])
    return communication


@transaction.atomic
def dispatch_due_communications(limit: int = 100) -> int:
    now = timezone.now()
    pending = CommunicationLog.objects.filter(
        status=CommunicationLog.Status.PENDING,
        direction=CommunicationLog.Direction.OUTBOUND,
        scheduled_at__lte=now,
    ).order_by("scheduled_at")[:limit]

    sent = 0
    for communication in pending:
        dispatch_communication(communication=communication)
        sent += 1

    reminders = Reminder.objects.filter(
        status=Reminder.ReminderStatus.DUE,
        due_at__lte=now,
    )[:limit]
    for reminder in reminders:
        reminder.status = Reminder.ReminderStatus.OVERDUE
        reminder.save(update_fields=["status", "updated_at"])

    return sent
