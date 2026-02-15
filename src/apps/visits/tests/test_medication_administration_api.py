from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inventory.models import Batch, InventoryItem, StockMovement
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import MedicationAdministration, Prescription, Visit


class MedicationAdministrationApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.mar@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Mar", last_name="Owner", phone="+79990001003")
        pet = Pet.objects.create(
            owner=owner,
            name="Ares",
            species=Pet.Species.DOG,
            microchip_id="900000000001003",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.prescription = Prescription.objects.create(
            visit=visit,
            medication_name="Antibiotic",
            dosage="50 mg",
            frequency="BID",
            duration_days=5,
        )

        self.inventory_item = InventoryItem.objects.create(
            name="Antibiotic vial",
            sku="ABX-VIAL-TEST",
            category=InventoryItem.Category.MEDICINE,
            unit="ml",
            min_stock=Decimal("0"),
        )
        self.batch = Batch.objects.create(
            item=self.inventory_item,
            lot_number="LOT-ABX-001",
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
        )

        self.administration = MedicationAdministration.objects.create(
            prescription=self.prescription,
            inventory_item=self.inventory_item,
            dose_amount=Decimal("1"),
            dose_unit="ml",
        )

    def test_mark_given_writes_off_stock(self):
        response = self.client.post(
            f"/api/medication-administrations/{self.administration.id}/mark-given/",
            {"quantity_written_off": "1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.administration.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(self.administration.status, MedicationAdministration.AdministrationStatus.GIVEN)
        self.assertEqual(self.batch.quantity_available, Decimal("9"))
        self.assertTrue(
            StockMovement.objects.filter(
                reference_type="MedicationAdministration",
                reference_id=str(self.administration.id),
            ).exists()
        )
