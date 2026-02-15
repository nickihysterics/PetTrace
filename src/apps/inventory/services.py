from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import InventoryItem, StockMovement


@transaction.atomic
def write_off_inventory_item(
    *,
    item: InventoryItem,
    quantity: Decimal | int | float | str,
    reason: str = "",
    moved_by=None,
    reference_type: str = "",
    reference_id: str = "",
    allow_expired: bool = False,
) -> list[StockMovement]:
    qty = Decimal(str(quantity))
    if qty <= 0:
        raise ValidationError("quantity must be positive")

    remaining = qty
    movements: list[StockMovement] = []

    batches = item.batches.filter(quantity_available__gt=0).order_by("expires_at", "created_at")
    for batch in batches:
        if not allow_expired and batch.is_expired:
            continue
        if remaining <= 0:
            break

        deduct = min(batch.quantity_available, remaining)
        if deduct <= 0:
            continue

        batch.quantity_available -= deduct
        batch.save(update_fields=["quantity_available", "updated_at"])

        movement = StockMovement.objects.create(
            item=item,
            batch=batch,
            movement_type=StockMovement.MovementType.WRITE_OFF,
            quantity=deduct,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            moved_by=moved_by,
        )
        movements.append(movement)

        remaining -= deduct

    if remaining > 0:
        raise ValidationError("insufficient stock")

    return movements