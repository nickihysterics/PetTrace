from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel
from apps.pets.models import Pet


class LabOrder(PublicUUIDModel, TimeStampedModel):
    class LabOrderStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        COLLECTED = "COLLECTED", "Collected"
        IN_TRANSPORT = "IN_TRANSPORT", "In Transport"
        RECEIVED = "RECEIVED", "Received"
        IN_PROCESS = "IN_PROCESS", "In Process"
        DONE = "DONE", "Done"
        REJECTED = "REJECTED", "Rejected"
        CANCELED = "CANCELED", "Canceled"

    ALLOWED_TRANSITIONS = {
        LabOrderStatus.PLANNED: {LabOrderStatus.COLLECTED, LabOrderStatus.CANCELED},
        LabOrderStatus.COLLECTED: {LabOrderStatus.IN_TRANSPORT, LabOrderStatus.REJECTED},
        LabOrderStatus.IN_TRANSPORT: {LabOrderStatus.RECEIVED, LabOrderStatus.REJECTED},
        LabOrderStatus.RECEIVED: {LabOrderStatus.IN_PROCESS, LabOrderStatus.REJECTED},
        LabOrderStatus.IN_PROCESS: {LabOrderStatus.DONE, LabOrderStatus.REJECTED},
        LabOrderStatus.DONE: set(),
        LabOrderStatus.REJECTED: set(),
        LabOrderStatus.CANCELED: set(),
    }

    visit = models.ForeignKey("visits.Visit", on_delete=models.CASCADE, related_name="lab_orders")
    ordered_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ordered_lab_orders",
    )
    status = models.CharField(max_length=16, choices=LabOrderStatus.choices, default=LabOrderStatus.PLANNED, db_index=True)
    notes = models.TextField(blank=True)
    ordered_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    sla_minutes = models.PositiveIntegerField(default=60)

    class Meta:
        ordering = ["-ordered_at"]
        permissions = [
            ("approve_lab_result", "Can approve lab result"),
        ]

    def __str__(self) -> str:
        return f"LabOrder #{self.pk} for Visit #{self.visit_id}"

    def transition_to(self, new_status: str) -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(f"Переход из статуса {self.status} в {new_status} запрещен")
        if new_status == self.LabOrderStatus.DONE:
            self.completed_at = timezone.now()
        self.status = new_status


class LabTest(PublicUUIDModel, TimeStampedModel):
    class LabTestStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PROCESS = "IN_PROCESS", "In Process"
        DONE = "DONE", "Done"
        REJECTED = "REJECTED", "Rejected"

    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="tests")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=LabTestStatus.choices, default=LabTestStatus.PLANNED)
    specimen_type = models.CharField(max_length=64)
    turnaround_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ["name"]
        unique_together = [("lab_order", "code")]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Specimen(PublicUUIDModel, TimeStampedModel):
    class SpecimenStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        COLLECTED = "COLLECTED", "Collected"
        IN_TRANSPORT = "IN_TRANSPORT", "In Transport"
        RECEIVED = "RECEIVED", "Received"
        IN_PROCESS = "IN_PROCESS", "In Process"
        DONE = "DONE", "Done"
        REJECTED = "REJECTED", "Rejected"

    class RejectionReason(models.TextChoices):
        HEMOLYZED = "HEMOLYZED", "Hemolyzed"
        INSUFFICIENT_VOLUME = "INSUFFICIENT_VOLUME", "Insufficient Volume"
        CONTAMINATED = "CONTAMINATED", "Contaminated"
        EXPIRED = "EXPIRED", "Expired"
        OTHER = "OTHER", "Other"

    ALLOWED_TRANSITIONS = {
        SpecimenStatus.PLANNED: {SpecimenStatus.COLLECTED, SpecimenStatus.REJECTED},
        SpecimenStatus.COLLECTED: {SpecimenStatus.IN_TRANSPORT, SpecimenStatus.REJECTED},
        SpecimenStatus.IN_TRANSPORT: {SpecimenStatus.RECEIVED, SpecimenStatus.REJECTED},
        SpecimenStatus.RECEIVED: {SpecimenStatus.IN_PROCESS, SpecimenStatus.REJECTED},
        SpecimenStatus.IN_PROCESS: {SpecimenStatus.DONE, SpecimenStatus.REJECTED},
        SpecimenStatus.DONE: set(),
        SpecimenStatus.REJECTED: set(),
    }

    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="specimens")
    specimen_type = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=SpecimenStatus.choices, default=SpecimenStatus.PLANNED, db_index=True)
    collected_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="collected_specimens",
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    in_process_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    collection_room = models.CharField(max_length=64, blank=True)
    rejection_reason = models.CharField(max_length=32, choices=RejectionReason.choices, blank=True)
    rejection_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Specimen #{self.pk} ({self.specimen_type})"

    def transition_to(self, new_status: str) -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(f"Переход из статуса {self.status} в {new_status} запрещен")

        now = timezone.now()
        if new_status == self.SpecimenStatus.COLLECTED and self.collected_at is None:
            self.collected_at = now
        if new_status == self.SpecimenStatus.RECEIVED and self.received_at is None:
            self.received_at = now
        if new_status == self.SpecimenStatus.IN_PROCESS and self.in_process_at is None:
            self.in_process_at = now
        if new_status in {self.SpecimenStatus.DONE, self.SpecimenStatus.REJECTED} and self.done_at is None:
            self.done_at = now

        self.status = new_status


class Tube(PublicUUIDModel, TimeStampedModel):
    class TubeType(models.TextChoices):
        EDTA = "EDTA", "EDTA"
        SERUM = "SERUM", "Serum"
        URINE = "URINE", "Urine"
        STOOL = "STOOL", "Stool"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=64, unique=True)
    tube_type = models.CharField(max_length=16, choices=TubeType.choices)
    lot_number = models.CharField(max_length=64)
    expires_at = models.DateField(null=True, blank=True)
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lab_tubes",
    )

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class SpecimenTube(PublicUUIDModel, TimeStampedModel):
    specimen = models.ForeignKey(Specimen, on_delete=models.CASCADE, related_name="specimen_tubes")
    tube = models.ForeignKey(Tube, on_delete=models.PROTECT, related_name="usage_records")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("specimen", "tube")]


class ContainerLabel(PublicUUIDModel, TimeStampedModel):
    specimen = models.OneToOneField(Specimen, on_delete=models.CASCADE, related_name="label")
    label_value = models.CharField(max_length=255, unique=True)
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.label_value


class SpecimenEvent(PublicUUIDModel, TimeStampedModel):
    specimen = models.ForeignKey(Specimen, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    actor = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)
    event_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-event_at"]


class SpecimenRecollection(PublicUUIDModel, TimeStampedModel):
    class RecollectionStatus(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CREATED = "CREATED", "Created"
        COLLECTED = "COLLECTED", "Collected"
        CANCELED = "CANCELED", "Canceled"

    original_specimen = models.ForeignKey(
        Specimen,
        on_delete=models.CASCADE,
        related_name="recollection_requests",
    )
    recollected_specimen = models.OneToOneField(
        Specimen,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recollection_parent",
    )
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=RecollectionStatus.choices, default=RecollectionStatus.REQUESTED)
    requested_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requested_recollections",
    )
    requested_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"Recollection for specimen #{self.original_specimen_id}"


class LabParameterReference(PublicUUIDModel, TimeStampedModel):
    parameter_name = models.CharField(max_length=128)
    species = models.CharField(max_length=16, choices=Pet.Species.choices, blank=True)
    min_age_months = models.PositiveIntegerField(null=True, blank=True)
    max_age_months = models.PositiveIntegerField(null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    reference_low = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    reference_high = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    critical_low = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    critical_high = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["parameter_name", "species", "min_age_months"]

    def __str__(self) -> str:
        return f"{self.parameter_name} ({self.species or 'ANY'})"


class LabResultValue(PublicUUIDModel, TimeStampedModel):
    class Flag(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name="result_values")
    parameter_name = models.CharField(max_length=128)
    value = models.CharField(max_length=128)
    unit = models.CharField(max_length=32, blank=True)
    reference_range = models.CharField(max_length=120, blank=True)
    flag = models.CharField(max_length=16, choices=Flag.choices, default=Flag.NORMAL)
    parameter_reference = models.ForeignKey(
        LabParameterReference,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="results",
    )
    source = models.CharField(max_length=32, default="MANUAL")
    comment = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_lab_results",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True)

    class Meta:
        ordering = ["parameter_name"]

    def __str__(self) -> str:
        return f"{self.parameter_name}: {self.value}"
