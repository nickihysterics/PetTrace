from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.facilities.models import Branch, Cabinet
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Appointment


class AppointmentScopeActionTests(APITestCase):
    def setUp(self):
        start_1 = timezone.datetime(2026, 2, 13, 10, 0, tzinfo=timezone.get_current_timezone())
        start_2 = timezone.datetime(2026, 2, 13, 11, 0, tzinfo=timezone.get_current_timezone())

        self.branch = Branch.objects.create(code="MAIN", name="Main branch")
        self.consult_cabinet = Cabinet.objects.create(
            branch=self.branch,
            code="C101",
            name="Consult room",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        self.lab_cabinet = Cabinet.objects.create(
            branch=self.branch,
            code="L201",
            name="Lab room",
            cabinet_type=Cabinet.CabinetType.LAB,
        )

        owner = Owner.objects.create(first_name="Roman", last_name="Vet", phone="+79995550011")
        pet = Pet.objects.create(
            owner=owner,
            name="Mia",
            species=Pet.Species.CAT,
            microchip_id="900000000000211",
        )

        self.consult_appointment = Appointment.objects.create(
            owner=owner,
            pet=pet,
            branch=self.branch,
            cabinet=self.consult_cabinet,
            start_at=start_1,
            service_type="Consultation",
        )
        self.lab_appointment = Appointment.objects.create(
            owner=owner,
            pet=pet,
            branch=self.branch,
            cabinet=self.lab_cabinet,
            start_at=start_2,
            service_type="Lab work",
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="assistant.scope@pettrace.local",
            password="test12345",
        )
        group, _ = Group.objects.get_or_create(name="assistant")
        self.user.groups.add(group)
        self._grant_perm("visits", "view_appointment")
        self._grant_perm("visits", "change_appointment")
        self._grant_perm("visits", "add_visit")

    def _grant_perm(self, app_label: str, codename: str):
        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        self.user.user_permissions.add(permission)

    def test_assistant_cannot_start_visit_for_out_of_scope_lab_cabinet(self):
        self.client.force_authenticate(self.user)

        list_response = self.client.get("/api/appointments/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in list_response.data}
        self.assertSetEqual(returned_ids, {self.consult_appointment.id})

        blocked_response = self.client.post(
            f"/api/appointments/{self.lab_appointment.id}/start-visit/",
            {},
            format="json",
        )
        self.assertEqual(blocked_response.status_code, status.HTTP_404_NOT_FOUND)

        allowed_response = self.client.post(
            f"/api/appointments/{self.consult_appointment.id}/start-visit/",
            {},
            format="json",
        )
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
