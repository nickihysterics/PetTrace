from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.facilities.models import Branch, Cabinet
from apps.users.models import UserAccessProfile


class CabinetScopeApiTests(APITestCase):
    def setUp(self):
        self.main_branch = Branch.objects.create(code="MAIN", name="Main branch")
        self.secondary_branch = Branch.objects.create(code="SEC", name="Secondary branch")

        self.consult_main = Cabinet.objects.create(
            branch=self.main_branch,
            code="C101",
            name="Consult 101",
            cabinet_type=Cabinet.CabinetType.CONSULTATION,
        )
        self.lab_main = Cabinet.objects.create(
            branch=self.main_branch,
            code="L201",
            name="Lab 201",
            cabinet_type=Cabinet.CabinetType.LAB,
        )
        self.lab_secondary = Cabinet.objects.create(
            branch=self.secondary_branch,
            code="L301",
            name="Lab 301",
            cabinet_type=Cabinet.CabinetType.LAB,
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="lab.scope@pettrace.local",
            password="test12345",
        )
        group, _ = Group.objects.get_or_create(name="lab_technician")
        self.user.groups.add(group)
        self._grant_perm("facilities", "view_cabinet")

    def _grant_perm(self, app_label: str, codename: str):
        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        self.user.user_permissions.add(permission)

    def test_lab_technician_sees_only_lab_cabinets(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/cabinets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(returned_ids, {self.lab_main.id, self.lab_secondary.id})

    def test_profile_can_limit_user_to_assigned_cabinets(self):
        profile = UserAccessProfile.objects.create(
            user=self.user,
            home_branch=self.main_branch,
            limit_to_assigned_cabinets=True,
        )
        profile.allowed_cabinets.add(self.lab_main)

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/cabinets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(returned_ids, {self.lab_main.id})
