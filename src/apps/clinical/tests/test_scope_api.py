from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinical.models import (
    ClinicalAlert,
    ProcedureChecklist,
    ProcedureChecklistItem,
    ProcedureChecklistTemplate,
    ProcedureChecklistTemplateItem,
)
from apps.facilities.models import Branch, Cabinet
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.users.models import UserAccessProfile
from apps.visits.models import ProcedureOrder, Visit


class ClinicalScopeApiTests(APITestCase):
    def setUp(self):
        self.allowed_branch = Branch.objects.create(code="ALWB", name="Allowed branch")
        self.allowed_cabinet = Cabinet.objects.create(
            branch=self.allowed_branch,
            code="A101",
            name="Allowed cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        self.denied_branch = Branch.objects.create(code="DNYB", name="Denied branch")
        self.denied_cabinet = Cabinet.objects.create(
            branch=self.denied_branch,
            code="D101",
            name="Denied cabinet",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )

        owner = Owner.objects.create(first_name="Scope", last_name="Clinical", phone="+79990002001")
        pet = Pet.objects.create(
            owner=owner,
            name="ScopePet",
            species=Pet.Species.CAT,
            microchip_id="900000000002001",
        )

        self.allowed_visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=self.allowed_branch,
            cabinet=self.allowed_cabinet,
        )
        self.denied_visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
            branch=self.denied_branch,
            cabinet=self.denied_cabinet,
        )

        self.allowed_procedure = ProcedureOrder.objects.create(
            visit=self.allowed_visit,
            name="Allowed procedure",
            status=ProcedureOrder.ProcedureStatus.PLANNED,
        )
        self.denied_procedure = ProcedureOrder.objects.create(
            visit=self.denied_visit,
            name="Denied procedure",
            status=ProcedureOrder.ProcedureStatus.PLANNED,
        )

        self.allowed_alert = ClinicalAlert.objects.create(
            visit=self.allowed_visit,
            severity=ClinicalAlert.Severity.WARNING,
            message="Allowed alert",
        )
        ClinicalAlert.objects.create(
            visit=self.denied_visit,
            severity=ClinicalAlert.Severity.WARNING,
            message="Denied alert",
        )

        allowed_checklist = ProcedureChecklist.objects.create(procedure_order=self.allowed_procedure)
        denied_checklist = ProcedureChecklist.objects.create(procedure_order=self.denied_procedure)
        self.allowed_item = ProcedureChecklistItem.objects.create(
            checklist=allowed_checklist,
            title="Allowed item",
            is_required=True,
        )
        ProcedureChecklistItem.objects.create(
            checklist=denied_checklist,
            title="Denied item",
            is_required=True,
        )

        self.template = ProcedureChecklistTemplate.objects.create(
            name="Procedure checklist template",
            procedure_name="Generic procedure",
            is_active=True,
        )
        ProcedureChecklistTemplateItem.objects.create(
            template=self.template,
            title="Prep patient",
            is_required=True,
            sort_order=1,
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="scope.clinical@pettrace.local",
            password="test",
        )
        self._grant_perm("clinical", "view_clinicalalert")
        self._grant_perm("clinical", "view_procedurechecklistitem")
        self._grant_perm("clinical", "add_procedurechecklist")

        profile = UserAccessProfile.objects.create(
            user=self.user,
            home_branch=self.allowed_branch,
            limit_to_assigned_cabinets=True,
        )
        profile.allowed_branches.add(self.allowed_branch)
        profile.allowed_cabinets.add(self.allowed_cabinet)

        self.client.force_authenticate(self.user)

    def _grant_perm(self, app_label: str, codename: str):
        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        self.user.user_permissions.add(permission)

    def test_alert_list_is_limited_by_branch_cabinet_scope(self):
        response = self.client.get("/api/clinical/alerts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(returned_ids, {self.allowed_alert.id})

    def test_checklist_item_list_is_limited_by_branch_cabinet_scope(self):
        response = self.client.get("/api/clinical/checklist-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(returned_ids, {self.allowed_item.id})

    def test_create_from_template_denies_out_of_scope_procedure_order(self):
        response = self.client.post(
            "/api/clinical/checklists/create-from-template/",
            {
                "procedure_order": self.denied_procedure.id,
                "template": self.template.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Нет доступа", str(response.data))

    def test_create_from_template_allows_in_scope_procedure_order(self):
        response = self.client.post(
            "/api/clinical/checklists/create-from-template/",
            {
                "procedure_order": self.allowed_procedure.id,
                "template": self.template.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["procedure_order"], self.allowed_procedure.id)
        self.assertEqual(len(response.data["items"]), 1)
