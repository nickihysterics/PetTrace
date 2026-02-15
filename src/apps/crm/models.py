from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class OwnerTag(PublicUUIDModel, TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)
    color = models.CharField(max_length=16, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OwnerTagAssignment(PublicUUIDModel, TimeStampedModel):
    owner = models.ForeignKey("owners.Owner", on_delete=models.CASCADE, related_name="tag_assignments")
    tag = models.ForeignKey(OwnerTag, on_delete=models.CASCADE, related_name="owner_assignments")

    class Meta:
        unique_together = [("owner", "tag")]
        ordering = ["owner", "tag"]

    def __str__(self) -> str:
        return f"{self.owner_id}:{self.tag.name}"


class CommunicationLog(PublicUUIDModel, TimeStampedModel):
    class Channel(models.TextChoices):
        SMS = "SMS", "SMS"
        EMAIL = "EMAIL", "Email"
        PHONE = "PHONE", "Phone"
        TELEGRAM = "TELEGRAM", "Telegram"
        IN_APP = "IN_APP", "In-App"

    class Direction(models.TextChoices):
        OUTBOUND = "OUTBOUND", "Outbound"
        INBOUND = "INBOUND", "Inbound"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    owner = models.ForeignKey("owners.Owner", on_delete=models.CASCADE, related_name="communications")
    pet = models.ForeignKey("pets.Pet", null=True, blank=True, on_delete=models.SET_NULL, related_name="communications")
    visit = models.ForeignKey("visits.Visit", null=True, blank=True, on_delete=models.SET_NULL, related_name="communications")
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.EMAIL)
    direction = models.CharField(max_length=16, choices=Direction.choices, default=Direction.OUTBOUND)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_communications")
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_at", "-created_at"]
        permissions = [
            ("dispatch_communication", "Can dispatch communication"),
        ]

    def __str__(self) -> str:
        return f"{self.channel}:{self.owner_id}:{self.status}"


class Reminder(PublicUUIDModel, TimeStampedModel):
    class ReminderType(models.TextChoices):
        VACCINATION = "VACCINATION", "Vaccination"
        FOLLOW_UP = "FOLLOW_UP", "Follow Up"
        CHECKUP = "CHECKUP", "Checkup"
        OTHER = "OTHER", "Other"

    class ReminderStatus(models.TextChoices):
        DUE = "DUE", "Due"
        SENT = "SENT", "Sent"
        DISMISSED = "DISMISSED", "Dismissed"
        OVERDUE = "OVERDUE", "Overdue"

    owner = models.ForeignKey("owners.Owner", on_delete=models.CASCADE, related_name="reminders")
    pet = models.ForeignKey("pets.Pet", null=True, blank=True, on_delete=models.SET_NULL, related_name="reminders")
    visit = models.ForeignKey("visits.Visit", null=True, blank=True, on_delete=models.SET_NULL, related_name="reminders")
    reminder_type = models.CharField(max_length=16, choices=ReminderType.choices, default=ReminderType.OTHER)
    status = models.CharField(max_length=16, choices=ReminderStatus.choices, default=ReminderStatus.DUE)
    due_at = models.DateTimeField()
    message = models.CharField(max_length=255)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.reminder_type}:{self.owner_id}:{self.status}"
