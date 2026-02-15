from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel


class PriceItem(PublicUUIDModel, TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class DiscountRule(PublicUUIDModel, TimeStampedModel):
    class RuleScope(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        OWNER = "OWNER", "Owner"
        OWNER_TAG = "OWNER_TAG", "Owner Tag"
        PROMO = "PROMO", "Promo"

    class DiscountType(models.TextChoices):
        PERCENT = "PERCENT", "Percent"
        FIXED = "FIXED", "Fixed"

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=16, choices=RuleScope.choices, default=RuleScope.GLOBAL)
    discount_type = models.CharField(max_length=16, choices=DiscountType.choices, default=DiscountType.PERCENT)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    owner = models.ForeignKey(
        "owners.Owner",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discount_rules",
    )
    owner_tag = models.ForeignKey(
        "crm.OwnerTag",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discount_rules",
    )
    promo_code = models.CharField(max_length=64, blank=True, db_index=True)
    min_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    auto_apply = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def calculate_discount_amount(self, subtotal: Decimal) -> Decimal:
        if subtotal <= 0:
            return Decimal("0")
        if subtotal < self.min_subtotal:
            return Decimal("0")
        if self.discount_type == self.DiscountType.PERCENT:
            return subtotal * (self.value / Decimal("100"))
        return min(self.value, subtotal)


class Invoice(PublicUUIDModel, TimeStampedModel):
    class InvoiceStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FORMED = "FORMED", "Formed"
        POSTED = "POSTED", "Posted"
        PAID = "PAID", "Paid"
        CANCELED = "CANCELED", "Canceled"

    visit = models.OneToOneField("visits.Visit", on_delete=models.CASCADE, related_name="invoice")
    status = models.CharField(max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    applied_discount_rule = models.ForeignKey(
        DiscountRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applied_invoices",
    )
    discount_code = models.CharField(max_length=64, blank=True)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    formed_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invoice #{self.pk}"

    def recalculate_totals(self):
        subtotal = sum(
            (
                line.line_total
                for line in self.lines.filter(is_void=False)
            ),
            Decimal("0"),
        )
        self.subtotal_amount = subtotal
        discount_ratio = self.discount_percent / Decimal("100")
        percent_discount = subtotal * discount_ratio
        discount_fixed = self.discount_amount or Decimal("0")
        total = subtotal - percent_discount - discount_fixed
        self.total_amount = max(total, Decimal("0"))
        return self.total_amount


class InvoiceLine(PublicUUIDModel, TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    price_item = models.ForeignKey(PriceItem, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    is_void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.description


class Payment(PublicUUIDModel, TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        TRANSFER = "TRANSFER", "Transfer"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)
    external_id = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self) -> str:
        return f"Payment #{self.pk}"


class PaymentAdjustment(PublicUUIDModel, TimeStampedModel):
    class AdjustmentType(models.TextChoices):
        REFUND = "REFUND", "Refund"
        CORRECTION = "CORRECTION", "Correction"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="adjustments")
    adjustment_type = models.CharField(max_length=16, choices=AdjustmentType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    adjusted_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_adjustments",
    )
    adjusted_at = models.DateTimeField(default=timezone.now)
    external_reference = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-adjusted_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.adjustment_type} {self.amount}"
