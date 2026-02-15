from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import decorators, response, status

from apps.common.viewsets import RBACModelViewSet, RBACReadOnlyModelViewSet

from .models import Batch, InventoryItem, StockMovement
from .serializers import BatchSerializer, InventoryItemSerializer, StockMovementSerializer
from .services import write_off_inventory_item


class InventoryItemViewSet(RBACModelViewSet):
    queryset = InventoryItem.objects.prefetch_related("batches").all()
    serializer_class = InventoryItemSerializer
    filterset_fields = ["category", "is_active"]
    search_fields = ["sku", "name"]
    action_permission_map = {
        "write_off": ["write_off_stock"],
    }

    @decorators.action(detail=True, methods=["post"], url_path="write-off")
    @transaction.atomic
    def write_off(self, request, pk=None):
        item = self.get_object()
        quantity = Decimal(str(request.data.get("quantity", "0")))
        reason = request.data.get("reason", "")

        try:
            movements = write_off_inventory_item(
                item=item,
                quantity=quantity,
                reason=reason,
                moved_by=request.user if request.user.is_authenticated else None,
                reference_type=request.data.get("reference_type", "manual"),
                reference_id=request.data.get("reference_id", ""),
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        return response.Response(
            {
                "item": item.id,
                "written_off": str(quantity),
                "movements": StockMovementSerializer(movements, many=True).data,
            }
        )


class BatchViewSet(RBACModelViewSet):
    queryset = Batch.objects.select_related("item").all()
    serializer_class = BatchSerializer
    filterset_fields = ["item", "item__category", "lot_number"]
    search_fields = ["item__sku", "item__name", "lot_number", "supplier"]


class StockMovementViewSet(RBACReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("item", "batch", "moved_by").all()
    serializer_class = StockMovementSerializer
    filterset_fields = ["item", "movement_type", "batch"]
    search_fields = ["item__sku", "item__name", "reference_type", "reference_id", "reason"]
    ordering_fields = ["created_at"]
