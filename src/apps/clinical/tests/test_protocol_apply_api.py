from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinical.models import (
    ClinicalAlert,
    ClinicalProtocol,
    ContraindicationRule,
    ProtocolMedicationTemplate,
    ProtocolProcedureTemplate,
)
from apps.facilities.models import Branch, Cabinet
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.users.models import UserAccessProfile
from apps.visits.models import Visit


class ClinicalProtocolApplyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.clinical@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Anna", last_name="Clinical", phone="+79990000032")
        pet = Pet.objects.create(
            owner=owner,
            name="Mia",
            species=Pet.Species.CAT,
            microchip_id="900000000000132",
            weight_kg="4.00",
            allergies="penicillin allergy",
        )
        self.visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )

        self.protocol = ClinicalProtocol.objects.create(
            name="Gastro protocol",
            diagnosis_code="K52",
            diagnosis_title="Gastroenteritis",
            species=Pet.Species.CAT,
        )
        ProtocolMedicationTemplate.objects.create(
            protocol=self.protocol,
            medication_name="Amoxicillin",
            dose_mg_per_kg="12.5",
            frequency="BID",
            duration_days=5,
            route="oral",
        )
        ProtocolProcedureTemplate.objects.create(
            protocol=self.protocol,
            name="IV hydration",
            instructions="250 ml over 90 minutes",
        )
        ContraindicationRule.objects.create(
            medication_name="Amoxicillin",
            allergy_keyword="penicillin",
            species=Pet.Species.CAT,
            severity=ContraindicationRule.Severity.BLOCKING,
            message="Penicillin allergy contraindication",
        )

    def test_apply_protocol_creates_orders_and_alerts(self):
        response = self.client.post(
            f"/api/clinical/protocols/{self.protocol.id}/apply/",
            {"visit": self.visit.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["prescriptions_created"], 1)
        self.assertEqual(response.data["procedures_created"], 1)
        self.assertTrue(ClinicalAlert.objects.filter(visit=self.visit).exists())

    def test_dose_calc_endpoint(self):
        med_template = self.protocol.medication_templates.first()
        response = self.client.post(
            "/api/clinical/dose-calc/",
            {"medication_template": med_template.id, "weight_kg": "4.0"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recommended_dose_mg"], "50.00")

    def test_apply_protocol_respects_branch_cabinet_scope(self):
        user_model = get_user_model()
        scoped_user = user_model.objects.create_user(
            email="scoped.clinical@pettrace.local",
            password="test",
        )
        apply_perm = Permission.objects.get(
            content_type__app_label="clinical",
            codename="apply_clinical_protocol",
        )
        scoped_user.user_permissions.add(apply_perm)

        allowed_branch = Branch.objects.create(code="ALLOWED", name="Allowed branch")
        allowed_cabinet = Cabinet.objects.create(
            branch=allowed_branch,
            code="A101",
            name="Allowed cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        denied_branch = Branch.objects.create(code="DENIED", name="Denied branch")
        denied_cabinet = Cabinet.objects.create(
            branch=denied_branch,
            code="D101",
            name="Denied cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )

        owner = Owner.objects.create(first_name="Scope", last_name="Owner", phone="+79990005001")
        pet = Pet.objects.create(
            owner=owner,
            name="ScopePet",
            species=Pet.Species.CAT,
            microchip_id="900000000005001",
        )
        denied_visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=denied_branch,
            cabinet=denied_cabinet,
        )

        profile = UserAccessProfile.objects.create(
            user=scoped_user,
            home_branch=allowed_branch,
            limit_to_assigned_cabinets=True,
        )
        profile.allowed_branches.add(allowed_branch)
        profile.allowed_cabinets.add(allowed_cabinet)

        self.client.force_authenticate(scoped_user)
        response = self.client.post(
            f"/api/clinical/protocols/{self.protocol.id}/apply/",
            {"visit": denied_visit.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Нет доступа", str(response.data))
