from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import DocumentTemplate, GeneratedDocument
from apps.labs.models import LabOrder
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class DocumentTemplateGenerateApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.documents@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Doc", last_name="Owner", phone="+79990001002")
        pet = Pet.objects.create(
            owner=owner,
            name="Panda",
            species=Pet.Species.DOG,
            microchip_id="900000000001002",
        )
        self.visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.lab_order = LabOrder.objects.create(visit=self.visit)

        self.other_owner = Owner.objects.create(first_name="Other", last_name="Owner", phone="+79990001022")
        self.other_pet = Pet.objects.create(
            owner=self.other_owner,
            name="Koala",
            species=Pet.Species.CAT,
            microchip_id="900000000001022",
        )
        self.other_visit = Visit.objects.create(
            pet=self.other_pet,
            owner=self.other_owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.other_lab_order = LabOrder.objects.create(visit=self.other_visit)

        self.template = DocumentTemplate.objects.create(
            code="DISCHARGE_TEST",
            name="Discharge template",
            template_type=DocumentTemplate.TemplateType.DISCHARGE,
            body_template="Patient: {{ pet_name }}\nRecommendation: {{ recommendation }}",
        )

    def test_generate_template_document(self):
        response = self.client.post(
            f"/api/documents/templates/{self.template.id}/generate/",
            {
                "visit": self.visit.id,
                "payload": {
                    "pet_name": self.visit.pet.name,
                    "recommendation": "Hydration and rest",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        generated = GeneratedDocument.objects.get(id=response.data["id"])
        self.assertEqual(generated.template_id, self.template.id)
        self.assertEqual(generated.visit_id, self.visit.id)
        self.assertTrue(generated.file.name.endswith(".pdf"))

    def test_generate_with_unknown_owner_returns_404(self):
        response = self.client.post(
            f"/api/documents/templates/{self.template.id}/generate/",
            {"owner": 999999, "payload": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "owner not found")

    def test_generate_with_mismatched_owner_and_visit_returns_400(self):
        response = self.client.post(
            f"/api/documents/templates/{self.template.id}/generate/",
            {
                "visit": self.visit.id,
                "owner": self.other_owner.id,
                "payload": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner does not match selected visit context", response.data["detail"])

    def test_generate_with_mismatched_pet_and_visit_returns_400(self):
        response = self.client.post(
            f"/api/documents/templates/{self.template.id}/generate/",
            {
                "visit": self.visit.id,
                "pet": self.other_pet.id,
                "payload": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pet does not match selected visit context", response.data["detail"])

    def test_generate_with_mismatched_visit_and_lab_order_returns_400(self):
        response = self.client.post(
            f"/api/documents/templates/{self.template.id}/generate/",
            {
                "visit": self.visit.id,
                "lab_order": self.other_lab_order.id,
                "payload": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lab_order does not belong to selected visit", response.data["detail"])
