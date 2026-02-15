from rest_framework import serializers

from .models import Batch, InventoryItem, StockMovement


class InventoryItemSerializer(serializers.ModelSerializer):
    available_stock = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "public_id",
            "name",
            "sku",
            "category",
            "unit",
            "min_stock",
            "is_active",
            "available_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "available_stock", "created_at", "updated_at"]


class BatchSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Batch
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at", "is_expired"]


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]
