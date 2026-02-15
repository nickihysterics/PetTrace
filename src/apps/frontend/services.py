from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.labs.services import transition_lab_order, transition_specimen
from apps.visits.models import Appointment, Visit, VisitEvent
from apps.visits.queue import allocate_appointment_queue_number


def create_visit_event(
    *,
    visit: Visit,
    from_status: str,
    to_status: str,
    actor=None,
    notes: str = "",
) -> VisitEvent:
    return VisitEvent.objects.create(
        visit=visit,
        from_status=from_status,
        to_status=to_status,
        actor=actor if actor and actor.is_authenticated else None,
        notes=notes,
    )


@transaction.atomic
def check_in_appointment(*, appointment: Appointment) -> Appointment:
    if appointment.status not in {
        Appointment.AppointmentStatus.BOOKED,
        Appointment.AppointmentStatus.CHECKED_IN,
    }:
        raise ValidationError(f"Нельзя отметить запись в статусе {appointment.status}")

    if appointment.status == Appointment.AppointmentStatus.BOOKED:
        appointment.transition_to(Appointment.AppointmentStatus.CHECKED_IN)

    if appointment.queue_number is None:
        appointment.queue_number = allocate_appointment_queue_number(
            appointment=appointment
        )

    appointment.save(update_fields=["status", "checked_in_at", "queue_number", "updated_at"])
    return appointment


@transaction.atomic
def start_visit_from_appointment(
    *,
    appointment: Appointment,
    actor=None,
    chief_complaint: str = "",
) -> Visit:
    if appointment.visit_id is not None:
        return appointment.visit

    if appointment.status in {
        Appointment.AppointmentStatus.CANCELED,
        Appointment.AppointmentStatus.NO_SHOW,
        Appointment.AppointmentStatus.COMPLETED,
    }:
        raise ValidationError(f"Нельзя начать визит из статуса записи {appointment.status}")

    if appointment.status == Appointment.AppointmentStatus.BOOKED:
        appointment.transition_to(Appointment.AppointmentStatus.CHECKED_IN)
    if appointment.status == Appointment.AppointmentStatus.CHECKED_IN:
        appointment.transition_to(Appointment.AppointmentStatus.IN_ROOM)

    visit = Visit.objects.create(
        pet=appointment.pet,
        owner=appointment.owner,
        veterinarian=appointment.veterinarian,
        status=Visit.VisitStatus.WAITING,
        branch=appointment.branch,
        cabinet=appointment.cabinet,
        room=appointment.room,
        scheduled_at=appointment.start_at,
        chief_complaint=chief_complaint,
    )

    previous = visit.status
    visit.transition_to(Visit.VisitStatus.IN_PROGRESS)
    visit.save(update_fields=["status", "started_at", "updated_at"])
    create_visit_event(
        visit=visit,
        from_status=previous,
        to_status=visit.status,
        actor=actor,
        notes="Визит начат из записи",
    )

    appointment.visit = visit
    appointment.save(update_fields=["status", "checked_in_at", "visit", "updated_at"])
    return visit


@transaction.atomic
def complete_appointment(*, appointment: Appointment, actor=None) -> Appointment:
    if appointment.status != Appointment.AppointmentStatus.IN_ROOM:
        raise ValidationError("Запись должна быть в статусе IN_ROOM для завершения")

    appointment.transition_to(Appointment.AppointmentStatus.COMPLETED)
    appointment.save(update_fields=["status", "completed_at", "updated_at"])

    if appointment.visit and appointment.visit.status == Visit.VisitStatus.IN_PROGRESS:
        previous = appointment.visit.status
        appointment.visit.transition_to(Visit.VisitStatus.COMPLETED)
        appointment.visit.save(update_fields=["status", "ended_at", "updated_at"])
        create_visit_event(
            visit=appointment.visit,
            from_status=previous,
            to_status=appointment.visit.status,
            actor=actor,
            notes="Визит автоматически завершен из записи",
        )

    return appointment


@transaction.atomic
def transition_appointment_status(*, appointment: Appointment, new_status: str) -> Appointment:
    appointment.transition_to(new_status)
    appointment.save(update_fields=["status", "checked_in_at", "completed_at", "updated_at"])
    return appointment


@transaction.atomic
def transition_visit_status(*, visit: Visit, new_status: str, actor=None, notes: str = "") -> Visit:
    previous = visit.status
    visit.transition_to(new_status)
    visit.save(update_fields=["status", "started_at", "ended_at", "updated_at"])
    create_visit_event(
        visit=visit,
        from_status=previous,
        to_status=visit.status,
        actor=actor,
        notes=notes,
    )
    return visit


__all__ = [
    "check_in_appointment",
    "complete_appointment",
    "start_visit_from_appointment",
    "transition_appointment_status",
    "transition_lab_order",
    "transition_specimen",
    "transition_visit_status",
]
