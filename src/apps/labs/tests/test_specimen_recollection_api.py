from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.labs.models import LabOrder, Specimen, SpecimenRecollection
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class SpecimenRecollectionApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.recollection@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Re", last_name="Collect", phone="+79990001001")
        pet = Pet.objects.create(
            owner=owner,
            name="Ruby",
            species=Pet.Species.CAT,
            microchip_id="900000000001001",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.order = LabOrder.objects.create(visit=visit)
        self.specimen = Specimen.objects.create(
            lab_order=self.order,
            specimen_type="blood",
            status=Specimen.SpecimenStatus.REJECTED,
            rejection_reason=Specimen.RejectionReason.HEMOLYZED,
        )

    def test_request_recollection_creates_new_specimen(self):
        response = self.client.post(
            f"/api/specimens/{self.specimen.id}/request-recollection/",
            {"reason": "Hemolyzed specimen"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("new_specimen", response.data)
        self.assertIn("recollection", response.data)

        recollection = SpecimenRecollection.objects.get(original_specimen=self.specimen)
        self.assertEqual(recollection.status, SpecimenRecollection.RecollectionStatus.CREATED)
        self.assertIsNotNone(recollection.recollected_specimen_id)
        self.assertEqual(
            recollection.recollected_specimen.status,
            Specimen.SpecimenStatus.PLANNED,
        )
