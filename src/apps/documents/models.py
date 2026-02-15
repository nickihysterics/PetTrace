import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class DocumentStoragePolicy(PublicUUIDModel, TimeStampedModel):
    class StorageBackend(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        S3 = "S3", "S3-compatible"

    name = models.CharField(max_length=128, unique=True)
    storage_backend = models.CharField(max_length=16, choices=StorageBackend.choices, default=StorageBackend.LOCAL)
    max_file_size_mb = models.PositiveIntegerField(default=20)
    allowed_mime_types = models.JSONField(default=list, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ClinicalDocument(PublicUUIDModel, TimeStampedModel):
    class DocumentType(models.TextChoices):
        XRAY = "XRAY", "X-Ray"
        ULTRASOUND = "ULTRASOUND", "Ultrasound"
        PHOTO = "PHOTO", "Photo"
        PDF_RESULT = "PDF_RESULT", "PDF Result"
        DISCHARGE = "DISCHARGE", "Discharge"
        OTHER = "OTHER", "Other"

    document_uid = models.UUIDField(default=uuid.uuid4, db_index=True)
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions",
    )

    document_type = models.CharField(max_length=16, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="clinical-documents/")
    mime_type = models.CharField(max_length=128, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    storage_policy = models.ForeignKey(
        DocumentStoragePolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )

    pet = models.ForeignKey(
        "pets.Pet",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="clinical_documents",
    )
    visit = models.ForeignKey(
        "visits.Visit",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    lab_order = models.ForeignKey(
        "labs.LabOrder",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    uploaded_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_documents",
    )
    replaced_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaced_documents",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document_uid", "version"]),
            models.Index(fields=["document_type", "is_current"]),
        ]

    def __str__(self) -> str:
        return self.title or str(self.file)

    def clean(self):
        targets = [
            bool(self.pet_id),
            bool(self.visit_id),
            bool(self.lab_order_id),
        ]
        if sum(targets) == 0:
            raise ValidationError("Document must be linked to pet, visit or lab_order")
        if sum(targets) > 1:
            raise ValidationError("Document can be linked only to one target entity")

        if self.storage_policy and not self.storage_policy.is_active:
            raise ValidationError("Selected storage policy is inactive")

    def replace_with(self, *, new_document: "ClinicalDocument", actor=None):
        self.is_current = False
        self.replaced_at = timezone.now()
        self.replaced_by = actor
        self.save(update_fields=["is_current", "replaced_at", "replaced_by", "updated_at"])

        new_document.document_uid = self.document_uid
        new_document.version = self.version + 1
        new_document.previous_version = self
        new_document.is_current = True
        return new_document


class DocumentTemplate(PublicUUIDModel, TimeStampedModel):
    class TemplateType(models.TextChoices):
        CONSENT = "CONSENT", "Consent"
        DISCHARGE = "DISCHARGE", "Discharge"
        SERVICE_ACT = "SERVICE_ACT", "Service Act"
        LAB_REFERRAL = "LAB_REFERRAL", "Lab Referral"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=16, choices=TemplateType.choices, default=TemplateType.OTHER)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class GeneratedDocument(PublicUUIDModel, TimeStampedModel):
    template = models.ForeignKey(
        DocumentTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_documents",
    )
    visit = models.ForeignKey(
        "visits.Visit",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="generated_documents",
    )
    owner = models.ForeignKey(
        "owners.Owner",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="generated_documents",
    )
    pet = models.ForeignKey(
        "pets.Pet",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="generated_documents",
    )
    lab_order = models.ForeignKey(
        "labs.LabOrder",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="generated_documents",
    )
    payload = models.JSONField(default=dict, blank=True)
    file = models.FileField(upload_to="generated-documents/")
    generated_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_documents",
    )
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"GeneratedDocument #{self.id}"
