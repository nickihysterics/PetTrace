from django.contrib import admin

from .models import Batch, InventoryItem, StockMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["id", "sku", "name", "category", "min_stock", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["sku", "name"]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["id", "item", "lot_number", "expires_at", "quantity_received", "quantity_available"]
    list_filter = ["expires_at", "item__category"]
    search_fields = ["item__sku", "item__name", "lot_number"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["id", "item", "batch", "movement_type", "quantity", "moved_by", "created_at"]
    list_filter = ["movement_type"]
    search_fields = ["item__sku", "item__name", "reference_type", "reference_id"]
