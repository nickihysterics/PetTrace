from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import PublicUUIDModel, TimeStampedModel


class Organization(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Branch(PublicUUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="branches",
    )
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Cabinet(PublicUUIDModel, TimeStampedModel):
    class CabinetType(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Consultation"
        PROCEDURE = "PROCEDURE", "Procedure"
        LAB = "LAB", "Laboratory"
        SURGERY = "SURGERY", "Surgery"
        INPATIENT = "INPATIENT", "Inpatient"
        OTHER = "OTHER", "Other"

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="cabinets")
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    cabinet_type = models.CharField(max_length=16, choices=CabinetType.choices, default=CabinetType.CONSULTATION)
    capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["branch__name", "code"]
        unique_together = [("branch", "code")]
        indexes = [
            models.Index(fields=["branch", "cabinet_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.branch.code}:{self.code}"


class EquipmentType(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Equipment(PublicUUIDModel, TimeStampedModel):
    class EquipmentStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        IN_USE = "IN_USE", "In Use"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of Service"

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="equipment")
    cabinet = models.ForeignKey(
        Cabinet,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment",
    )
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.PROTECT, related_name="equipment")
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=EquipmentStatus.choices, default=EquipmentStatus.AVAILABLE)
    is_active = models.BooleanField(default=True)
    last_maintenance_at = models.DateTimeField(null=True, blank=True)
    next_maintenance_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["branch__name", "name"]
        indexes = [
            models.Index(fields=["branch", "equipment_type", "status", "is_active"]),
        ]

    def clean(self):
        if self.cabinet and self.cabinet.branch_id != self.branch_id:
            raise ValidationError("equipment.cabinet must belong to the same branch")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ServiceRequirement(PublicUUIDModel, TimeStampedModel):
    service = models.OneToOneField(
        "Service",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="requirement",
    )
    service_type = models.CharField(max_length=128, blank=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    required_cabinet_type = models.CharField(max_length=16, choices=Cabinet.CabinetType.choices, blank=True)
    default_duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["service_type"]

    def __str__(self) -> str:
        return self.display_service_type

    @property
    def display_service_type(self) -> str:
        if self.service_id:
            return self.service.code
        return self.service_type

    def clean(self):
        if not self.service_id and not self.service_type:
            raise ValidationError("Должно быть заполнено service или service_type")


class Service(PublicUUIDModel, TimeStampedModel):
    class ServiceCategory(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Consultation"
        LAB = "LAB", "Laboratory"
        PROCEDURE = "PROCEDURE", "Procedure"
        SURGERY = "SURGERY", "Surgery"
        HOSPITAL = "HOSPITAL", "Hospital"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=16, choices=ServiceCategory.choices, default=ServiceCategory.OTHER)
    description = models.TextField(blank=True)
    default_duration_minutes = models.PositiveIntegerField(default=30)
    price_item = models.ForeignKey(
        "billing.PriceItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="services",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ServiceRequirementEquipment(PublicUUIDModel, TimeStampedModel):
    requirement = models.ForeignKey(
        ServiceRequirement,
        on_delete=models.CASCADE,
        related_name="required_equipment",
    )
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        related_name="service_requirements",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("requirement", "equipment_type")]
        ordering = ["requirement__service_type", "equipment_type__name"]

    def __str__(self) -> str:
        return f"{self.requirement.display_service_type} -> {self.equipment_type.code} x{self.quantity}"


class HospitalWard(PublicUUIDModel, TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="wards")
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["branch__name", "code"]
        unique_together = [("branch", "code")]

    def __str__(self) -> str:
        return f"{self.branch.code}:{self.code}"


class HospitalBed(PublicUUIDModel, TimeStampedModel):
    class BedStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        CLEANING = "CLEANING", "Cleaning"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of Service"

    ward = models.ForeignKey(HospitalWard, on_delete=models.PROTECT, related_name="beds")
    cabinet = models.ForeignKey(
        Cabinet,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hospital_beds",
    )
    code = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=BedStatus.choices, default=BedStatus.AVAILABLE)
    is_isolation = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ward__branch__name", "ward__code", "code"]
        unique_together = [("ward", "code")]
        indexes = [
            models.Index(fields=["ward", "status", "is_active"]),
        ]

    def clean(self):
        if self.cabinet and self.cabinet.branch_id != self.ward.branch_id:
            raise ValidationError("hospital_bed.cabinet must belong to the same branch as ward")

    def __str__(self) -> str:
        return f"{self.ward.branch.code}:{self.ward.code}:{self.code}"
