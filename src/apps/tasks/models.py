from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class Task(PublicUUIDModel, TimeStampedModel):
    class TaskType(models.TextChoices):
        COLLECT_SPECIMEN = "COLLECT_SPECIMEN", "Collect Specimen"
        PROCEDURE = "PROCEDURE", "Procedure"
        LAB_RECEIVE = "LAB_RECEIVE", "Lab Receive"
        FOLLOW_UP = "FOLLOW_UP", "Follow Up"
        OTHER = "OTHER", "Other"

    class TaskStatus(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=32, choices=TaskType.choices, default=TaskType.OTHER)
    status = models.CharField(max_length=16, choices=TaskStatus.choices, default=TaskStatus.TODO)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)

    visit = models.ForeignKey("visits.Visit", null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    lab_order = models.ForeignKey("labs.LabOrder", null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    assigned_to = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_at", "-created_at"]

    def __str__(self) -> str:
        return self.title


class Notification(PublicUUIDModel, TimeStampedModel):
    class Channel(models.TextChoices):
        IN_APP = "IN_APP", "In-App"
        EMAIL = "EMAIL", "Email"
        TELEGRAM = "TELEGRAM", "Telegram"

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    recipient = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.IN_APP)
    title = models.CharField(max_length=255)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_sent(self):
        self.status = self.DeliveryStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.channel}: {self.title}"
