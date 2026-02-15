from rest_framework import serializers


class ReportPeriodSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    generated_at = serializers.DateTimeField()


class CountByStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class LabTurnaroundReportSerializer(ReportPeriodSerializer):
    total_orders = serializers.IntegerField()
    done_orders = serializers.IntegerField()
    status_breakdown = CountByStatusSerializer(many=True)
    avg_turnaround_minutes = serializers.FloatField(allow_null=True)
    median_turnaround_minutes = serializers.FloatField(allow_null=True)
    sla_breached_done = serializers.IntegerField()
    sla_breached_pending = serializers.IntegerField()


class TubeUsageByItemSerializer(serializers.Serializer):
    item__id = serializers.IntegerField()
    item__sku = serializers.CharField()
    item__name = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
    movements = serializers.IntegerField()


class LowStockItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    sku = serializers.CharField()
    name = serializers.CharField()
    available_stock = serializers.CharField()
    min_stock = serializers.CharField()


class TubeUsageReportSerializer(ReportPeriodSerializer):
    total_movements = serializers.IntegerField()
    total_written_off = serializers.CharField()
    usage_by_item = TubeUsageByItemSerializer(many=True)
    low_stock_items = LowStockItemSerializer(many=True)


class AppointmentOpsReportSerializer(ReportPeriodSerializer):
    total_appointments = serializers.IntegerField()
    linked_visits_count = serializers.IntegerField()
    no_show_count = serializers.IntegerField()
    no_show_rate_percent = serializers.FloatField()
    status_breakdown = CountByStatusSerializer(many=True)
    avg_checkin_to_start_minutes = serializers.FloatField(allow_null=True)
    avg_queue_number = serializers.FloatField(allow_null=True)


class PaymentMethodBreakdownSerializer(serializers.Serializer):
    method = serializers.CharField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    count = serializers.IntegerField()


class FinanceSummaryReportSerializer(ReportPeriodSerializer):
    invoice_count = serializers.IntegerField()
    payment_count = serializers.IntegerField()
    issued_amount = serializers.CharField()
    paid_amount = serializers.CharField()
    refund_amount = serializers.CharField()
    correction_amount = serializers.CharField()
    net_paid_amount = serializers.CharField()
    outstanding_amount = serializers.CharField()
    avg_invoice_amount = serializers.CharField()
    payment_method_breakdown = PaymentMethodBreakdownSerializer(many=True)
