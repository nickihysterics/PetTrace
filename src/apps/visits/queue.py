from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import Appointment, AppointmentQueueCounter


def _queue_date_for_appointment(appointment: Appointment):
    return timezone.localtime(appointment.start_at).date()


def allocate_appointment_queue_number(*, appointment: Appointment) -> int:
    queue_date = _queue_date_for_appointment(appointment)
    veterinarian = appointment.veterinarian

    with transaction.atomic():
        queryset = AppointmentQueueCounter.objects.select_for_update()
        try:
            counter = queryset.get(
                veterinarian=veterinarian,
                queue_date=queue_date,
            )
        except AppointmentQueueCounter.DoesNotExist:
            try:
                counter = AppointmentQueueCounter.objects.create(
                    veterinarian=veterinarian,
                    queue_date=queue_date,
                    last_number=0,
                )
            except IntegrityError:
                counter = queryset.get(
                    veterinarian=veterinarian,
                    queue_date=queue_date,
                )

        AppointmentQueueCounter.objects.filter(id=counter.id).update(
            last_number=F("last_number") + 1,
        )
        counter.refresh_from_db(fields=["last_number"])
        return counter.last_number
