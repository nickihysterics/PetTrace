from django.contrib import admin

from .models import DiscountRule, Invoice, InvoiceLine, Payment, PaymentAdjustment, PriceItem


@admin.register(PriceItem)
class PriceItemAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "amount", "currency", "is_active"]
    list_filter = ["currency", "is_active"]
    search_fields = ["code", "name"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "status", "subtotal_amount", "total_amount", "formed_at", "posted_at"]
    list_filter = ["status"]
    search_fields = ["visit__pet__name", "visit__owner__phone"]


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ["id", "invoice", "description", "quantity", "unit_price", "line_total", "is_void"]
    list_filter = ["is_void"]
    search_fields = ["description", "void_reason"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "invoice", "method", "amount", "paid_at"]
    list_filter = ["method"]
    search_fields = ["external_id"]


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "scope", "discount_type", "value", "auto_apply", "is_active"]
    list_filter = ["scope", "discount_type", "auto_apply", "is_active"]
    search_fields = ["code", "name", "promo_code"]


@admin.register(PaymentAdjustment)
class PaymentAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["id", "payment", "adjustment_type", "amount", "reason", "adjusted_by", "adjusted_at"]
    list_filter = ["adjustment_type"]
    search_fields = ["reason", "external_reference"]
