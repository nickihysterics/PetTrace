from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.facilities.models import Branch, Cabinet
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Appointment, AppointmentQueueCounter


class AppointmentQueueNumberingApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            email="admin.queue@pettrace.local",
            password="test",
        )
        self.vet_a = user_model.objects.create_user(
            email="vet.a.queue@pettrace.local",
            password="test",
        )
        self.vet_b = user_model.objects.create_user(
            email="vet.b.queue@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.admin)

        self.branch = Branch.objects.create(code="QUEUE", name="Queue branch")
        self.cabinet = Cabinet.objects.create(
            branch=self.branch,
            code="Q101",
            name="Queue cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        owner = Owner.objects.create(first_name="Queue", last_name="Owner", phone="+79990003001")
        pet = Pet.objects.create(
            owner=owner,
            name="QueuePet",
            species=Pet.Species.CAT,
            microchip_id="900000000003001",
        )

        start_at = timezone.make_aware(datetime(2026, 2, 13, 10, 0))
        self.appointment_a1 = Appointment.objects.create(
            owner=owner,
            pet=pet,
            veterinarian=self.vet_a,
            branch=self.branch,
            cabinet=self.cabinet,
            start_at=start_at,
        )
        self.appointment_a2 = Appointment.objects.create(
            owner=owner,
            pet=pet,
            veterinarian=self.vet_a,
            branch=self.branch,
            cabinet=self.cabinet,
            start_at=start_at + timedelta(minutes=30),
        )
        self.appointment_b1 = Appointment.objects.create(
            owner=owner,
            pet=pet,
            veterinarian=self.vet_b,
            branch=self.branch,
            cabinet=self.cabinet,
            start_at=start_at + timedelta(minutes=60),
        )
        self.queue_date = timezone.localtime(start_at).date()

    def test_queue_numbers_are_stable_and_independent_per_veterinarian(self):
        first_check_in = self.client.post(
            f"/api/appointments/{self.appointment_a1.id}/check-in/",
            {},
            format="json",
        )
        self.assertEqual(first_check_in.status_code, status.HTTP_200_OK)
        self.assertEqual(first_check_in.data["queue_number"], 1)

        repeated_check_in = self.client.post(
            f"/api/appointments/{self.appointment_a1.id}/check-in/",
            {},
            format="json",
        )
        self.assertEqual(repeated_check_in.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated_check_in.data["queue_number"], 1)

        second_check_in_same_vet = self.client.post(
            f"/api/appointments/{self.appointment_a2.id}/check-in/",
            {},
            format="json",
        )
        self.assertEqual(second_check_in_same_vet.status_code, status.HTTP_200_OK)
        self.assertEqual(second_check_in_same_vet.data["queue_number"], 2)

        first_check_in_other_vet = self.client.post(
            f"/api/appointments/{self.appointment_b1.id}/check-in/",
            {},
            format="json",
        )
        self.assertEqual(first_check_in_other_vet.status_code, status.HTTP_200_OK)
        self.assertEqual(first_check_in_other_vet.data["queue_number"], 1)

        self.assertTrue(
            AppointmentQueueCounter.objects.filter(
                queue_date=self.queue_date,
                veterinarian=self.vet_a,
                last_number=2,
            ).exists()
        )
        self.assertTrue(
            AppointmentQueueCounter.objects.filter(
                queue_date=self.queue_date,
                veterinarian=self.vet_b,
                last_number=1,
            ).exists()
        )
