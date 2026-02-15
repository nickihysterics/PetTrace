from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.facilities.models import Branch
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Hospitalization, Visit


class HospitalizationFlowTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.hospital@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        branch = Branch.objects.create(code="HOSP", name="Hospital Branch")
        owner = Owner.objects.create(first_name="In", last_name="Patient", phone="+79990000034")
        pet = Pet.objects.create(
            owner=owner,
            name="Baxter",
            species=Pet.Species.DOG,
            microchip_id="900000000000134",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=branch,
        )
        self.hospitalization = Hospitalization.objects.create(visit=visit, branch=branch, cage_number="A1")

    def test_hospitalization_transition(self):
        response = self.client.post(
            f"/api/hospitalizations/{self.hospitalization.id}/transition/",
            {"status": Hospitalization.HospitalizationStatus.UNDER_OBSERVATION},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        discharge = self.client.post(
            f"/api/hospitalizations/{self.hospitalization.id}/transition/",
            {"status": Hospitalization.HospitalizationStatus.DISCHARGED},
            format="json",
        )
        self.assertEqual(discharge.status_code, status.HTTP_200_OK)
        self.hospitalization.refresh_from_db()
        self.assertEqual(self.hospitalization.status, Hospitalization.HospitalizationStatus.DISCHARGED)
        self.assertIsNotNone(self.hospitalization.discharged_at)
