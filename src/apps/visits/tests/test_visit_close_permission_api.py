from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class VisitClosePermissionTests(APITestCase):
    def setUp(self):
        self.owner = Owner.objects.create(
            first_name="Anna",
            last_name="Sidorova",
            phone="+79991230002",
        )
        self.pet = Pet.objects.create(
            owner=self.owner,
            name="Rex",
            species=Pet.Species.DOG,
            microchip_id="900000000000102",
        )
        self.visit = Visit.objects.create(
            pet=self.pet,
            owner=self.owner,
            status=Visit.VisitStatus.COMPLETED,
        )

        user_model = get_user_model()
        self.assistant = user_model.objects.create_user(
            email="assistant.close@pettrace.local",
            password="test",
        )
        self.veterinarian = user_model.objects.create_user(
            email="vet.close@pettrace.local",
            password="test",
        )

        self._grant_perm(self.assistant, "visits", "change_visit")
        self._grant_perm(self.veterinarian, "visits", "change_visit")
        self._grant_perm(self.veterinarian, "visits", "close_visit")

    def _grant_perm(self, user, app_label: str, codename: str):
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        user.user_permissions.add(perm)

    def test_user_without_close_visit_permission_gets_403(self):
        self.client.force_authenticate(self.assistant)

        response = self.client.post(
            f"/api/encounters/{self.visit.id}/transition/",
            {"status": Visit.VisitStatus.CLOSED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.VisitStatus.COMPLETED)

    def test_user_with_close_visit_permission_can_close_visit(self):
        self.client.force_authenticate(self.veterinarian)

        response = self.client.post(
            f"/api/encounters/{self.visit.id}/transition/",
            {"status": Visit.VisitStatus.CLOSED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.VisitStatus.CLOSED)
        self.assertIsNotNone(self.visit.ended_at)
