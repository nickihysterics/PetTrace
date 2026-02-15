import uuid

from django.core.validators import RegexValidator
from django.db import models

from apps.common.models import PublicUUIDModel, TimeStampedModel

MICROCHIP_VALIDATOR = RegexValidator(
    regex=r"^\d{15}$",
    message="ID микрочипа должен содержать ровно 15 цифр.",
)


class Pet(PublicUUIDModel, TimeStampedModel):
    class Species(models.TextChoices):
        DOG = "DOG", "Dog"
        CAT = "CAT", "Cat"
        RABBIT = "RABBIT", "Rabbit"
        BIRD = "BIRD", "Bird"
        OTHER = "OTHER", "Other"

    class Sex(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        UNKNOWN = "UNKNOWN", "Unknown"

    class PetStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DECEASED = "DECEASED", "Deceased"
        ARCHIVED = "ARCHIVED", "Archived"

    owner = models.ForeignKey("owners.Owner", on_delete=models.PROTECT, related_name="pets")
    name = models.CharField(max_length=120)
    species = models.CharField(max_length=16, choices=Species.choices)
    breed = models.CharField(max_length=120, blank=True)
    sex = models.CharField(max_length=16, choices=Sex.choices, default=Sex.UNKNOWN)
    birth_date = models.DateField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    allergies = models.TextField(blank=True)
    vaccination_notes = models.TextField(blank=True)
    insurance_number = models.CharField(max_length=64, blank=True)

    microchip_id = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        validators=[MICROCHIP_VALIDATOR],
        db_index=True,
    )
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    status = models.CharField(max_length=16, choices=PetStatus.choices, default=PetStatus.ACTIVE)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["species", "breed"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner})"


class PetAttachment(PublicUUIDModel, TimeStampedModel):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="pets/attachments/")
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or str(self.file)
