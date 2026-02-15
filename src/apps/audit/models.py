from django.conf import settings
from django.db import models

from apps.common.models import PublicUUIDModel, TimeStampedModel


class AuditLog(PublicUUIDModel, TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        STATUS_CHANGE = "STATUS_CHANGE", "Status Change"
        API_MUTATION = "API_MUTATION", "API Mutation"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.API_MUTATION)
    model_label = models.CharField(max_length=128)
    object_pk = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.model_label} {self.object_pk}"
