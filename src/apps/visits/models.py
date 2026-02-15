from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class Visit(PublicUUIDModel, TimeStampedModel):
    class VisitStatus(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        WAITING = "WAITING", "Waiting"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CLOSED = "CLOSED", "Closed"
        CANCELED = "CANCELED", "Canceled"

    ALLOWED_TRANSITIONS = {
        VisitStatus.SCHEDULED: {VisitStatus.WAITING, VisitStatus.CANCELED},
        VisitStatus.WAITING: {VisitStatus.IN_PROGRESS, VisitStatus.CANCELED},
        VisitStatus.IN_PROGRESS: {VisitStatus.COMPLETED, VisitStatus.CANCELED},
        VisitStatus.COMPLETED: {VisitStatus.CLOSED},
        VisitStatus.CLOSED: set(),
        VisitStatus.CANCELED: set(),
    }

    pet = models.ForeignKey("pets.Pet", on_delete=models.PROTECT, related_name="visits")
    owner = models.ForeignKey("owners.Owner", on_delete=models.PROTECT, related_name="visits")
    veterinarian = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_visits",
    )
    assistant = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assisted_visits",
    )

    status = models.CharField(max_length=16, choices=VisitStatus.choices, default=VisitStatus.SCHEDULED, db_index=True)
    branch = models.ForeignKey(
        "facilities.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visits",
    )
    cabinet = models.ForeignKey(
        "facilities.Cabinet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visits",
    )
    room = models.CharField(max_length=64, blank=True)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    chief_complaint = models.TextField(blank=True)
    anamnesis = models.TextField(blank=True)
    physical_exam = models.TextField(blank=True)
    diagnosis_summary = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("close_visit", "Can close visit"),
        ]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["branch", "cabinet", "scheduled_at"]),
        ]

    def __str__(self) -> str:
        return f"Visit #{self.pk} - {self.pet.name}"

    def transition_to(self, new_status: str) -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(f"Переход из статуса {self.status} в {new_status} запрещен")

        now = timezone.now()
        if new_status == self.VisitStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = now
        if new_status in {self.VisitStatus.COMPLETED, self.VisitStatus.CLOSED, self.VisitStatus.CANCELED}:
            self.ended_at = now

        self.status = new_status


class Appointment(PublicUUIDModel, TimeStampedModel):
    class AppointmentStatus(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        IN_ROOM = "IN_ROOM", "In Room"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"
        NO_SHOW = "NO_SHOW", "No Show"

    ALLOWED_TRANSITIONS = {
        AppointmentStatus.BOOKED: {AppointmentStatus.CHECKED_IN, AppointmentStatus.CANCELED, AppointmentStatus.NO_SHOW},
        AppointmentStatus.CHECKED_IN: {AppointmentStatus.IN_ROOM, AppointmentStatus.CANCELED},
        AppointmentStatus.IN_ROOM: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELED},
        AppointmentStatus.COMPLETED: set(),
        AppointmentStatus.CANCELED: set(),
        AppointmentStatus.NO_SHOW: set(),
    }

    owner = models.ForeignKey("owners.Owner", on_delete=models.PROTECT, related_name="appointments")
    pet = models.ForeignKey("pets.Pet", on_delete=models.PROTECT, related_name="appointments")
    veterinarian = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_appointments",
    )

    service_type = models.CharField(max_length=128, blank=True)
    service = models.ForeignKey(
        "facilities.Service",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )
    branch = models.ForeignKey(
        "facilities.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )
    cabinet = models.ForeignKey(
        "facilities.Cabinet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )
    room = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)

    queue_number = models.PositiveIntegerField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.BOOKED,
        db_index=True,
    )

    visit = models.OneToOneField(
        Visit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointment",
    )

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["veterinarian", "start_at"]),
            models.Index(fields=["branch", "cabinet", "start_at"]),
        ]

    def __str__(self) -> str:
        return f"Appointment #{self.id} {self.pet.name}"

    def transition_to(self, new_status: str) -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(f"Переход из статуса {self.status} в {new_status} запрещен")

        now = timezone.now()
        if new_status == self.AppointmentStatus.CHECKED_IN and self.checked_in_at is None:
            self.checked_in_at = now
        if new_status in {self.AppointmentStatus.COMPLETED, self.AppointmentStatus.CANCELED, self.AppointmentStatus.NO_SHOW}:
            self.completed_at = now

        self.status = new_status


class AppointmentQueueCounter(TimeStampedModel):
    veterinarian = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="appointment_queue_counters",
    )
    queue_date = models.DateField(db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-queue_date", "veterinarian_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinarian", "queue_date"],
                condition=models.Q(veterinarian__isnull=False),
                name="visits_appointment_queue_counter_unique",
            ),
            models.UniqueConstraint(
                fields=["queue_date"],
                condition=models.Q(veterinarian__isnull=True),
                name="visits_appointment_queue_counter_unassigned_unique",
            ),
        ]

    def __str__(self) -> str:
        vet_repr = self.veterinarian_id or "any"
        return f"{self.queue_date} / {vet_repr}: {self.last_number}"


class VisitEvent(PublicUUIDModel, TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    actor = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    event_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-event_at"]


class Hospitalization(PublicUUIDModel, TimeStampedModel):
    class HospitalizationStatus(models.TextChoices):
        ADMITTED = "ADMITTED", "Admitted"
        UNDER_OBSERVATION = "UNDER_OBSERVATION", "Under Observation"
        CRITICAL = "CRITICAL", "Critical"
        DISCHARGED = "DISCHARGED", "Discharged"
        CANCELED = "CANCELED", "Canceled"

    ALLOWED_TRANSITIONS = {
        HospitalizationStatus.ADMITTED: {
            HospitalizationStatus.UNDER_OBSERVATION,
            HospitalizationStatus.CRITICAL,
            HospitalizationStatus.DISCHARGED,
            HospitalizationStatus.CANCELED,
        },
        HospitalizationStatus.UNDER_OBSERVATION: {
            HospitalizationStatus.CRITICAL,
            HospitalizationStatus.DISCHARGED,
            HospitalizationStatus.CANCELED,
        },
        HospitalizationStatus.CRITICAL: {
            HospitalizationStatus.UNDER_OBSERVATION,
            HospitalizationStatus.DISCHARGED,
            HospitalizationStatus.CANCELED,
        },
        HospitalizationStatus.DISCHARGED: set(),
        HospitalizationStatus.CANCELED: set(),
    }

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name="hospitalization")
    branch = models.ForeignKey("facilities.Branch", on_delete=models.PROTECT, related_name="hospitalizations")
    cabinet = models.ForeignKey(
        "facilities.Cabinet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hospitalizations",
    )
    current_bed = models.ForeignKey(
        "facilities.HospitalBed",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hospitalizations",
    )
    status = models.CharField(
        max_length=24,
        choices=HospitalizationStatus.choices,
        default=HospitalizationStatus.ADMITTED,
        db_index=True,
    )
    admitted_at = models.DateTimeField(default=timezone.now)
    discharged_at = models.DateTimeField(null=True, blank=True)
    cage_number = models.CharField(max_length=64, blank=True)
    care_plan = models.TextField(blank=True)
    feeding_instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["-admitted_at"]

    def transition_to(self, new_status: str):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(f"Переход из статуса {self.status} в {new_status} запрещен")
        if new_status in {self.HospitalizationStatus.DISCHARGED, self.HospitalizationStatus.CANCELED}:
            self.discharged_at = timezone.now()
        self.status = new_status


class HospitalBedStay(PublicUUIDModel, TimeStampedModel):
    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name="bed_stays")
    bed = models.ForeignKey("facilities.HospitalBed", on_delete=models.PROTECT, related_name="stays")
    moved_in_at = models.DateTimeField(default=timezone.now)
    moved_out_at = models.DateTimeField(null=True, blank=True)
    moved_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hospital_bed_moves",
    )
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-moved_in_at"]

    def __str__(self) -> str:
        return f"{self.hospitalization_id} -> {self.bed_id}"


class HospitalVitalRecord(PublicUUIDModel, TimeStampedModel):
    class AppetiteStatus(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        REDUCED = "REDUCED", "Reduced"
        ABSENT = "ABSENT", "Absent"

    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name="vitals")
    measured_at = models.DateTimeField(default=timezone.now)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_bpm = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    appetite_status = models.CharField(
        max_length=16,
        choices=AppetiteStatus.choices,
        default=AppetiteStatus.NORMAL,
    )
    water_intake_ml = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    urine_output_ml = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_hospital_vitals",
    )

    class Meta:
        ordering = ["-measured_at"]

    def __str__(self) -> str:
        return f"Vitals #{self.id} for hospitalization #{self.hospitalization_id}"


class HospitalProcedurePlan(PublicUUIDModel, TimeStampedModel):
    class PlanStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    hospitalization = models.ForeignKey(
        Hospitalization,
        on_delete=models.CASCADE,
        related_name="procedure_plans",
    )
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=PlanStatus.choices, default=PlanStatus.PLANNED)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_hospital_plans",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_at", "created_at"]

    def __str__(self) -> str:
        return self.title


class Diagnosis(PublicUUIDModel, TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="diagnoses")
    catalog_item = models.ForeignKey(
        "clinical.DiagnosisCatalog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="diagnoses",
    )
    code = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "title"]

    def __str__(self) -> str:
        return self.title


class Observation(PublicUUIDModel, TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="observations")
    symptom = models.ForeignKey(
        "clinical.SymptomCatalog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="observations",
    )
    name = models.CharField(max_length=120)
    value = models.CharField(max_length=120)
    unit = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class Prescription(PublicUUIDModel, TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="prescriptions")
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=120)
    frequency = models.CharField(max_length=120)
    duration_days = models.PositiveIntegerField(default=1)
    route = models.CharField(max_length=64, blank=True)
    warnings = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.medication_name


class MedicationAdministration(PublicUUIDModel, TimeStampedModel):
    class AdministrationStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        GIVEN = "GIVEN", "Given"
        SKIPPED = "SKIPPED", "Skipped"
        CANCELED = "CANCELED", "Canceled"

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="administrations")
    scheduled_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=16,
        choices=AdministrationStatus.choices,
        default=AdministrationStatus.PLANNED,
        db_index=True,
    )
    dose_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dose_unit = models.CharField(max_length=32, blank=True)
    route = models.CharField(max_length=64, blank=True)
    given_at = models.DateTimeField(null=True, blank=True)
    given_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="medication_administrations",
    )
    deviation_note = models.TextField(blank=True)
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="medication_administrations",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="medication_administrations",
    )
    quantity_written_off = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    write_off_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["scheduled_at", "created_at"]

    def __str__(self) -> str:
        return f"{self.prescription.medication_name} [{self.status}]"


class ProcedureOrder(PublicUUIDModel, TimeStampedModel):
    class ProcedureStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="procedures")
    name = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ProcedureStatus.choices, default=ProcedureStatus.PLANNED)
    performed_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="performed_procedures",
    )
    performed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
