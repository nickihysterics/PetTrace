from celery import shared_task
from django.utils import timezone

from apps.common.services import get_setting_int

from .models import AuditLog


@shared_task
def purge_audit_logs_task() -> dict:
    retention_days = get_setting_int("audit.retention_days", default=180)
    threshold = timezone.now() - timezone.timedelta(days=retention_days)
    deleted_count, _ = AuditLog.objects.filter(created_at__lt=threshold).delete()
    return {"retention_days": retention_days, "deleted": deleted_count}
