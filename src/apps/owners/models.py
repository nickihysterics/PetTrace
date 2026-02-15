from django.db import models

from apps.common.models import PublicUUIDModel, TimeStampedModel


class Owner(PublicUUIDModel, TimeStampedModel):
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, db_index=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_blacklisted = models.BooleanField(default=False)
    preferred_branch = models.ForeignKey(
        "facilities.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="preferred_owners",
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}".strip()


class ConsentDocument(PublicUUIDModel, TimeStampedModel):
    class ConsentType(models.TextChoices):
        PERSONAL_DATA = "PERSONAL_DATA", "Personal Data"
        SURGERY = "SURGERY", "Surgery"
        ANESTHESIA = "ANESTHESIA", "Anesthesia"
        GENERAL = "GENERAL", "General"

    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name="consents")
    consent_type = models.CharField(max_length=32, choices=ConsentType.choices)
    accepted_at = models.DateTimeField()
    document_file = models.FileField(upload_to="consents/", blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-accepted_at"]

    def __str__(self) -> str:
        return f"{self.owner} - {self.consent_type}"
