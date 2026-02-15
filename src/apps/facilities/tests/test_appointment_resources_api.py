from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.facilities.models import (
    Branch,
    Cabinet,
    Equipment,
    EquipmentType,
    ServiceRequirement,
    ServiceRequirementEquipment,
)
from apps.owners.models import Owner
from apps.pets.models import Pet


class AppointmentResourceValidationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.resources@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

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
        self.lab_cabinet_2 = Cabinet.objects.create(
            branch=self.branch,
            code="L202",
            name="Lab room 2",
            cabinet_type=Cabinet.CabinetType.LAB,
        )

        self.owner = Owner.objects.create(first_name="Olga", last_name="Ivanova", phone="+79990000031")
        self.pet = Pet.objects.create(
            owner=self.owner,
            name="Lucky",
            species=Pet.Species.DOG,
            microchip_id="900000000000131",
        )

    def test_overlapping_appointments_in_same_cabinet_are_blocked(self):
        payload = {
            "owner": self.owner.id,
            "pet": self.pet.id,
            "branch": self.branch.id,
            "cabinet": self.consult_cabinet.id,
            "service_type": "Consultation",
            "start_at": "2026-02-13T10:00:00+03:00",
            "duration_minutes": 30,
        }
        first = self.client.post("/api/appointments/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        overlap_payload = payload | {"start_at": "2026-02-13T10:15:00+03:00"}
        second = self.client.post("/api/appointments/", overlap_payload, format="json")

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("занят", str(second.data).lower())

    def test_service_requirement_cabinet_type_is_enforced(self):
        xray_type = EquipmentType.objects.create(code="XRAY", name="X-Ray")
        requirement = ServiceRequirement.objects.create(
            service_type="Xray",
            required_cabinet_type=Cabinet.CabinetType.LAB,
            default_duration_minutes=20,
        )
        ServiceRequirementEquipment.objects.create(
            requirement=requirement,
            equipment_type=xray_type,
            quantity=1,
        )
        Equipment.objects.create(
            branch=self.branch,
            cabinet=self.lab_cabinet,
            equipment_type=xray_type,
            code="XRAY-1",
            name="X-Ray unit 1",
        )

        wrong_payload = {
            "owner": self.owner.id,
            "pet": self.pet.id,
            "branch": self.branch.id,
            "cabinet": self.consult_cabinet.id,
            "service_type": "Xray",
            "start_at": "2026-02-13T11:00:00+03:00",
        }
        wrong_response = self.client.post("/api/appointments/", wrong_payload, format="json")
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("требует кабинет типа", str(wrong_response.data).lower())

        ok_payload = wrong_payload | {"cabinet": self.lab_cabinet.id}
        ok_response = self.client.post("/api/appointments/", ok_payload, format="json")
        self.assertEqual(ok_response.status_code, status.HTTP_201_CREATED)

    def test_equipment_capacity_is_enforced_for_overlapping_slots(self):
        xray_type = EquipmentType.objects.create(code="XRAY-CAP", name="X-Ray Capacity")
        requirement = ServiceRequirement.objects.create(
            service_type="XrayCapacity",
            required_cabinet_type=Cabinet.CabinetType.LAB,
            default_duration_minutes=30,
        )
        ServiceRequirementEquipment.objects.create(
            requirement=requirement,
            equipment_type=xray_type,
            quantity=1,
        )
        Equipment.objects.create(
            branch=self.branch,
            cabinet=self.lab_cabinet,
            equipment_type=xray_type,
            code="XRAY-CAP-1",
            name="X-Ray capacity unit",
        )

        first_payload = {
            "owner": self.owner.id,
            "pet": self.pet.id,
            "branch": self.branch.id,
            "cabinet": self.lab_cabinet.id,
            "service_type": "XrayCapacity",
            "start_at": "2026-02-13T12:00:00+03:00",
            "duration_minutes": 30,
        }
        first = self.client.post("/api/appointments/", first_payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second_payload = first_payload | {
            "cabinet": self.lab_cabinet_2.id,
            "start_at": "2026-02-13T12:05:00+03:00",
        }
        second = self.client.post("/api/appointments/", second_payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("недостаточно доступного оборудования", str(second.data).lower())

    def test_partial_update_uses_existing_time_window_for_resource_validation(self):
        first_payload = {
            "owner": self.owner.id,
            "pet": self.pet.id,
            "branch": self.branch.id,
            "cabinet": self.consult_cabinet.id,
            "service_type": "Consultation",
            "start_at": "2026-02-13T13:00:00+03:00",
            "duration_minutes": 30,
        }
        first = self.client.post("/api/appointments/", first_payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second_payload = first_payload | {
            "cabinet": self.lab_cabinet.id,
            "start_at": "2026-02-13T13:05:00+03:00",
        }
        second = self.client.post("/api/appointments/", second_payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        patch = self.client.patch(
            f"/api/appointments/{second.data['id']}/",
            {"cabinet": self.consult_cabinet.id},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("занят", str(patch.data).lower())
