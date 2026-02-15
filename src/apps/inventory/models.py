from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class InventoryItem(PublicUUIDModel, TimeStampedModel):
    class Category(models.TextChoices):
        MEDICINE = "MEDICINE", "Medicine"
        CONSUMABLE = "CONSUMABLE", "Consumable"
        LAB = "LAB", "Lab"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    unit = models.CharField(max_length=16, default="pcs")
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"

    @property
    def available_stock(self):
        return sum(batch.quantity_available for batch in self.batches.all())


class Batch(PublicUUIDModel, TimeStampedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="batches")
    lot_number = models.CharField(max_length=64)
    expires_at = models.DateField(null=True, blank=True)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["expires_at", "created_at"]
        unique_together = [("item", "lot_number")]

    def __str__(self) -> str:
        return f"{self.item.sku}:{self.lot_number}"

    def clean(self):
        if self.quantity_available > self.quantity_received:
            raise ValidationError("Количество в наличии не может превышать количество поступления")

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        return self.expires_at < timezone.localdate()


class StockMovement(PublicUUIDModel, TimeStampedModel):
    class MovementType(models.TextChoices):
        INBOUND = "INBOUND", "Inbound"
        WRITE_OFF = "WRITE_OFF", "Write Off"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        RESERVATION = "RESERVATION", "Reservation"
        RELEASE = "RELEASE", "Release"

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="movements")
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=16, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    reference_type = models.CharField(max_length=64, blank=True)
    reference_id = models.CharField(max_length=64, blank=True)
    moved_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("write_off_stock", "Can write off stock"),
        ]

    def __str__(self) -> str:
        return f"{self.movement_type} {self.quantity} {self.item.unit}"
