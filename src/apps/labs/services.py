from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.services import write_off_inventory_item
from apps.tasks.models import Notification, Task

from .models import LabOrder, LabParameterReference, LabResultValue, Specimen, SpecimenEvent


def _create_specimen_event(
    *,
    specimen: Specimen,
    from_status: str,
    to_status: str,
    actor=None,
    location: str = "",
    notes: str = "",
) -> SpecimenEvent:
    return SpecimenEvent.objects.create(
        specimen=specimen,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        location=location,
        notes=notes,
    )


def infer_lab_order_status(order: LabOrder) -> str:
    specimen_statuses = list(order.specimens.values_list("status", flat=True))
    if not specimen_statuses:
        return LabOrder.LabOrderStatus.PLANNED

    status_set = set(specimen_statuses)

    if Specimen.SpecimenStatus.REJECTED in status_set:
        return LabOrder.LabOrderStatus.REJECTED
    if status_set == {Specimen.SpecimenStatus.DONE}:
        return LabOrder.LabOrderStatus.DONE
    if Specimen.SpecimenStatus.IN_PROCESS in status_set:
        return LabOrder.LabOrderStatus.IN_PROCESS
    if Specimen.SpecimenStatus.RECEIVED in status_set:
        return LabOrder.LabOrderStatus.RECEIVED
    if Specimen.SpecimenStatus.IN_TRANSPORT in status_set:
        return LabOrder.LabOrderStatus.IN_TRANSPORT
    if Specimen.SpecimenStatus.COLLECTED in status_set:
        return LabOrder.LabOrderStatus.COLLECTED
    return LabOrder.LabOrderStatus.PLANNED


@transaction.atomic
def sync_lab_order_status(order: LabOrder) -> LabOrder:
    inferred = infer_lab_order_status(order)
    if inferred == order.status:
        return order

    order.status = inferred
    if inferred == LabOrder.LabOrderStatus.DONE:
        order.completed_at = timezone.now()
        order.save(update_fields=["status", "completed_at", "updated_at"])
    else:
        order.completed_at = None
        order.save(update_fields=["status", "completed_at", "updated_at"])
    return order


def ensure_collect_task(order: LabOrder) -> Task:
    existing = Task.objects.filter(
        lab_order=order,
        task_type=Task.TaskType.COLLECT_SPECIMEN,
        status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS],
    ).first()
    if existing:
        return existing

    return Task.objects.create(
        title=f"Забор образца для лабораторного заказа #{order.id}",
        description="Заберите материал, нанесите маркировку и подтвердите забор в ЛИС.",
        task_type=Task.TaskType.COLLECT_SPECIMEN,
        status=Task.TaskStatus.TODO,
        priority=Task.Priority.HIGH,
        visit=order.visit,
        lab_order=order,
        due_at=order.ordered_at + timedelta(minutes=15),
    )


def _close_collect_tasks_if_order_collected(order: LabOrder) -> None:
    has_pending_specimens = order.specimens.filter(status=Specimen.SpecimenStatus.PLANNED).exists()
    if has_pending_specimens:
        return

    now = timezone.now()
    Task.objects.filter(
        lab_order=order,
        task_type=Task.TaskType.COLLECT_SPECIMEN,
        status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS],
    ).update(status=Task.TaskStatus.DONE, completed_at=now, updated_at=now)

    Task.objects.get_or_create(
        lab_order=order,
        task_type=Task.TaskType.LAB_RECEIVE,
        status=Task.TaskStatus.TODO,
        defaults={
            "title": f"Receive lab order #{order.id}",
            "description": "Confirm specimen handoff and lab intake.",
            "priority": Task.Priority.MEDIUM,
            "visit": order.visit,
            "due_at": now + timedelta(minutes=10),
        },
    )


def _write_off_specimen_tubes(specimen: Specimen, actor=None) -> None:
    for specimen_tube in specimen.specimen_tubes.select_related("tube", "tube__inventory_item"):
        reference_type = "specimen_tube"
        reference_id = str(specimen_tube.public_id)
        already_written_off = StockMovement.objects.filter(
            reference_type=reference_type,
            reference_id=reference_id,
        ).exists()
        if already_written_off:
            continue

        item = specimen_tube.tube.inventory_item
        if item is None:
            item = InventoryItem.objects.filter(sku=specimen_tube.tube.code, is_active=True).first()
        if item is None:
            continue

        write_off_inventory_item(
            item=item,
            quantity=specimen_tube.quantity,
            reason=f"Auto write-off for specimen #{specimen.id}",
            moved_by=actor,
            reference_type=reference_type,
            reference_id=reference_id,
        )


@transaction.atomic
def process_collected_specimen_side_effects(specimen: Specimen, actor=None) -> None:
    if specimen.status != Specimen.SpecimenStatus.COLLECTED:
        return
    _write_off_specimen_tubes(specimen, actor=actor)
    _close_collect_tasks_if_order_collected(specimen.lab_order)
    sync_lab_order_status(specimen.lab_order)


@transaction.atomic
def transition_specimen(
    *,
    specimen: Specimen,
    new_status: str,
    actor=None,
    location: str = "",
    notes: str = "",
    sync_order: bool = True,
) -> Specimen:
    if specimen.status == new_status:
        return specimen

    previous_status = specimen.status
    specimen.transition_to(new_status)

    update_fields = ["status", "collected_at", "received_at", "in_process_at", "done_at", "updated_at"]
    if new_status == Specimen.SpecimenStatus.COLLECTED:
        if actor and specimen.collected_by_id is None:
            specimen.collected_by = actor
            update_fields.append("collected_by")
        if location:
            specimen.collection_room = location
            update_fields.append("collection_room")

    specimen.save(update_fields=update_fields)

    _create_specimen_event(
        specimen=specimen,
        from_status=previous_status,
        to_status=new_status,
        actor=actor,
        location=location,
        notes=notes,
    )

    if new_status == Specimen.SpecimenStatus.COLLECTED:
        process_collected_specimen_side_effects(specimen, actor=actor)

    if sync_order and new_status != Specimen.SpecimenStatus.COLLECTED:
        sync_lab_order_status(specimen.lab_order)

    return specimen


@transaction.atomic
def transition_lab_order(
    *,
    order: LabOrder,
    new_status: str,
    actor=None,
    location: str = "",
    notes: str = "",
) -> LabOrder:
    if order.status == new_status:
        return order

    previous_status = order.status
    order.transition_to(new_status)
    order.save(update_fields=["status", "completed_at", "updated_at"])

    for specimen in order.specimens.select_related("lab_order"):
        if specimen.status == new_status:
            continue
        allowed = Specimen.ALLOWED_TRANSITIONS.get(specimen.status, set())
        if new_status not in allowed:
            continue
        transition_specimen(
            specimen=specimen,
            new_status=new_status,
            actor=actor,
            location=location,
            notes=notes,
            sync_order=False,
        )

    # Сохраняем явно запрошенный переход, если нижележащие статусы не требуют более строгого.
    inferred = infer_lab_order_status(order)
    if inferred != new_status:
        order.status = inferred
        if inferred == LabOrder.LabOrderStatus.DONE:
            order.completed_at = timezone.now()
        order.save(update_fields=["status", "completed_at", "updated_at"])

    if previous_status == LabOrder.LabOrderStatus.PLANNED and new_status == LabOrder.LabOrderStatus.COLLECTED:
        _close_collect_tasks_if_order_collected(order)

    return order


def initialize_lab_order_workflow(order: LabOrder) -> None:
    ensure_collect_task(order)


def maybe_notify_critical_result(result: LabResultValue) -> None:
    if result.flag != LabResultValue.Flag.CRITICAL:
        return

    veterinarian = result.lab_test.lab_order.visit.veterinarian
    if veterinarian is None:
        return

    Notification.objects.create(
        recipient=veterinarian,
        channel=Notification.Channel.IN_APP,
        title="Обнаружено критическое лабораторное значение",
        body=(
            f"{result.parameter_name}={result.value}{result.unit or ''} "
            f"по заказу #{result.lab_test.lab_order_id} требует проверки."
        ),
        payload={
            "lab_order_id": result.lab_test.lab_order_id,
            "lab_test_id": result.lab_test_id,
            "result_id": result.id,
        },
        status=Notification.DeliveryStatus.PENDING,
    )


def _try_decimal(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    normalized = str(value).replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, TypeError):
        return None


def _resolve_parameter_reference(result: LabResultValue) -> LabParameterReference | None:
    visit = result.lab_test.lab_order.visit
    pet = getattr(visit, "pet", None)
    pet_species = getattr(pet, "species", "")
    pet_age_months = None
    if pet and pet.birth_date:
        today = timezone.localdate()
        months = (today.year - pet.birth_date.year) * 12 + (today.month - pet.birth_date.month)
        if today.day < pet.birth_date.day:
            months -= 1
        pet_age_months = max(months, 0)

    references = LabParameterReference.objects.filter(
        is_active=True,
        parameter_name__iexact=result.parameter_name,
    ).order_by("-species", "min_age_months")

    best_match = None
    for reference in references:
        if reference.species and reference.species != pet_species:
            continue
        if pet_age_months is not None and reference.min_age_months is not None and pet_age_months < reference.min_age_months:
            continue
        if pet_age_months is not None and reference.max_age_months is not None and pet_age_months > reference.max_age_months:
            continue
        if reference.unit and result.unit and reference.unit != result.unit:
            continue
        best_match = reference
        if reference.species == pet_species:
            break

    return best_match


def apply_reference_and_flag(result: LabResultValue) -> LabResultValue:
    reference = _resolve_parameter_reference(result)
    numeric_value = _try_decimal(result.value)
    new_flag = result.flag

    if reference:
        result.parameter_reference = reference
        if reference.reference_low is not None or reference.reference_high is not None:
            low = "" if reference.reference_low is None else str(reference.reference_low)
            high = "" if reference.reference_high is None else str(reference.reference_high)
            result.reference_range = f"{low}-{high}".strip("-")

        if numeric_value is not None:
            if reference.critical_low is not None and numeric_value <= reference.critical_low:
                new_flag = LabResultValue.Flag.CRITICAL
            elif reference.critical_high is not None and numeric_value >= reference.critical_high:
                new_flag = LabResultValue.Flag.CRITICAL
            elif reference.reference_low is not None and numeric_value < reference.reference_low:
                new_flag = LabResultValue.Flag.LOW
            elif reference.reference_high is not None and numeric_value > reference.reference_high:
                new_flag = LabResultValue.Flag.HIGH
            else:
                new_flag = LabResultValue.Flag.NORMAL

    if new_flag != result.flag or result.parameter_reference_id != getattr(reference, "id", None):
        result.flag = new_flag
        result.save(update_fields=["parameter_reference", "reference_range", "flag", "updated_at"])
    return result
