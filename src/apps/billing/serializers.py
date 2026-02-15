from rest_framework import serializers

from .models import DiscountRule, Invoice, InvoiceLine, Payment, PaymentAdjustment, PriceItem


class PriceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceItem
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class DiscountRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountRule
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "public_id", "subtotal_amount", "total_amount", "created_at", "updated_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = "__all__"
        read_only_fields = ["id", "public_id", "line_total", "created_at", "updated_at"]

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        unit_price = attrs.get("unit_price", getattr(self.instance, "unit_price", None))
        if quantity is None or quantity <= 0:
            raise serializers.ValidationError("quantity must be positive")
        if unit_price is None or unit_price < 0:
            raise serializers.ValidationError("unit_price must be non-negative")
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class PaymentAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAdjustment
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]
