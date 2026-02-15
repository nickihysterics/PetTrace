from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.labs.models import LabOrder, LabResultValue, LabTest
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class LabResultApprovalPermissionTests(APITestCase):
    def setUp(self):
        self.owner = Owner.objects.create(
            first_name="Ivan",
            last_name="Petrov",
            phone="+79991230001",
        )
        self.pet = Pet.objects.create(
            owner=self.owner,
            name="Milo",
            species=Pet.Species.CAT,
            microchip_id="900000000000101",
        )
        self.visit = Visit.objects.create(
            pet=self.pet,
            owner=self.owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.lab_order = LabOrder.objects.create(
            visit=self.visit,
            status=LabOrder.LabOrderStatus.PLANNED,
        )
        self.lab_test = LabTest.objects.create(
            lab_order=self.lab_order,
            code="CBC",
            name="Complete blood count",
            specimen_type="blood",
        )
        self.result = LabResultValue.objects.create(
            lab_test=self.lab_test,
            parameter_name="WBC",
            value="10.0",
        )

        user_model = get_user_model()
        self.assistant = user_model.objects.create_user(
            email="assistant.tests@pettrace.local",
            password="test",
        )
        self.lab_technician = user_model.objects.create_user(
            email="lab.tests@pettrace.local",
            password="test",
        )
        self._grant_perm(self.lab_technician, "labs", "approve_lab_result")

    def _grant_perm(self, user, app_label: str, codename: str):
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        user.user_permissions.add(perm)

    def test_user_without_approve_permission_gets_403(self):
        self.client.force_authenticate(self.assistant)

        response = self.client.post(
            f"/api/results/{self.result.id}/approve/",
            {"note": "approve"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.result.refresh_from_db()
        self.assertIsNone(self.result.approved_at)
        self.assertIsNone(self.result.approved_by_id)

    def test_user_with_approve_permission_can_approve_result(self):
        self.client.force_authenticate(self.lab_technician)

        response = self.client.post(
            f"/api/results/{self.result.id}/approve/",
            {"note": "validated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.result.refresh_from_db()
        self.assertEqual(self.result.approved_by_id, self.lab_technician.id)
        self.assertIsNotNone(self.result.approved_at)
        self.assertEqual(self.result.approval_note, "validated")
