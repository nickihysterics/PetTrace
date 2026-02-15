from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel
from apps.pets.models import Pet


class DiagnosisCatalog(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class SymptomCatalog(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ClinicalProtocol(PublicUUIDModel, TimeStampedModel):
    name = models.CharField(max_length=255)
    diagnosis_code = models.CharField(max_length=32, blank=True)
    diagnosis_title = models.CharField(max_length=255, blank=True)
    species = models.CharField(max_length=16, choices=Pet.Species.choices, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        permissions = [
            ("apply_clinical_protocol", "Can apply clinical protocol"),
        ]

    def __str__(self) -> str:
        return self.name


class ProtocolMedicationTemplate(PublicUUIDModel, TimeStampedModel):
    protocol = models.ForeignKey(
        ClinicalProtocol,
        on_delete=models.CASCADE,
        related_name="medication_templates",
    )
    medication_name = models.CharField(max_length=255)
    dose_mg_per_kg = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    fixed_dose_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    min_dose_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_dose_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    frequency = models.CharField(max_length=120, blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    route = models.CharField(max_length=64, blank=True)
    warnings = models.TextField(blank=True)

    class Meta:
        ordering = ["protocol", "medication_name"]

    def __str__(self) -> str:
        return f"{self.protocol.name}: {self.medication_name}"


class ProtocolProcedureTemplate(PublicUUIDModel, TimeStampedModel):
    protocol = models.ForeignKey(
        ClinicalProtocol,
        on_delete=models.CASCADE,
        related_name="procedure_templates",
    )
    name = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["protocol", "name"]

    def __str__(self) -> str:
        return f"{self.protocol.name}: {self.name}"


class ContraindicationRule(PublicUUIDModel, TimeStampedModel):
    class Severity(models.TextChoices):
        WARNING = "WARNING", "Warning"
        BLOCKING = "BLOCKING", "Blocking"

    medication_name = models.CharField(max_length=255)
    allergy_keyword = models.CharField(max_length=120, blank=True)
    species = models.CharField(max_length=16, choices=Pet.Species.choices, blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARNING)
    message = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["medication_name", "severity"]

    def __str__(self) -> str:
        return f"{self.medication_name} [{self.severity}]"


class ClinicalAlert(PublicUUIDModel, TimeStampedModel):
    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        BLOCKING = "BLOCKING", "Blocking"

    visit = models.ForeignKey("visits.Visit", on_delete=models.CASCADE, related_name="clinical_alerts")
    prescription = models.ForeignKey(
        "visits.Prescription",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="clinical_alerts",
    )
    rule = models.ForeignKey(
        ContraindicationRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARNING)
    message = models.TextField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_clinical_alerts",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.visit_id} {self.severity}: {self.message[:50]}"


class ProcedureChecklistTemplate(PublicUUIDModel, TimeStampedModel):
    name = models.CharField(max_length=255)
    procedure_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProcedureChecklistTemplateItem(PublicUUIDModel, TimeStampedModel):
    template = models.ForeignKey(
        ProcedureChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["template", "sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class ProcedureChecklist(PublicUUIDModel, TimeStampedModel):
    class ChecklistStatus(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    procedure_order = models.ForeignKey(
        "visits.ProcedureOrder",
        on_delete=models.CASCADE,
        related_name="checklists",
    )
    template = models.ForeignKey(
        ProcedureChecklistTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="checklists",
    )
    status = models.CharField(max_length=16, choices=ChecklistStatus.choices, default=ChecklistStatus.TODO)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Checklist #{self.id} for Procedure #{self.procedure_order_id}"

    def mark_done_if_completed(self):
        has_pending_required = self.items.filter(is_required=True, is_completed=False).exists()
        if has_pending_required:
            if self.status == self.ChecklistStatus.TODO:
                self.status = self.ChecklistStatus.IN_PROGRESS
                self.started_at = self.started_at or timezone.now()
                self.save(update_fields=["status", "started_at", "updated_at"])
            return False

        self.status = self.ChecklistStatus.DONE
        self.started_at = self.started_at or timezone.now()
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "started_at", "completed_at", "updated_at"])
        return True


class ProcedureChecklistItem(PublicUUIDModel, TimeStampedModel):
    checklist = models.ForeignKey(
        ProcedureChecklist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_checklist_items",
    )

    class Meta:
        ordering = ["checklist", "id"]

    def __str__(self) -> str:
        return self.title
