import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublicUUIDModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True


class SystemSetting(PublicUUIDModel, TimeStampedModel):
    class ValueType(models.TextChoices):
        STRING = "STRING", "String"
        BOOLEAN = "BOOLEAN", "Boolean"
        INTEGER = "INTEGER", "Integer"
        DECIMAL = "DECIMAL", "Decimal"
        JSON = "JSON", "JSON"

    key = models.CharField(max_length=128, unique=True)
    value_type = models.CharField(max_length=16, choices=ValueType.choices, default=ValueType.STRING)
    value_text = models.TextField(blank=True)
    value_json = models.JSONField(default=dict, blank=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class FeatureFlag(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code
