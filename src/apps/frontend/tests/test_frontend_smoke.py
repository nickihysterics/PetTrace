from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse


class FrontendSmokeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="frontend.user@pettrace.local",
            password="test12345",
        )

    def test_login_page_available(self):
        response = self.client.get(reverse("frontend:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Рабочая панель PetTrace")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("frontend:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("frontend:login"), response.url)

    def test_dashboard_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("frontend:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Операционный центр")

    def test_role_home_default_for_user_without_groups(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("frontend:role-home"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Мой кабинет")

    def test_role_home_for_specific_role(self):
        self.client.force_login(self.user)
        veterinarian_group, _ = Group.objects.get_or_create(name="veterinarian")
        self.user.groups.add(veterinarian_group)
        response = self.client.get(reverse("frontend:role-home-detail", kwargs={"role_key": "veterinarian"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Кабинет врача")

    def test_role_home_for_unassigned_role_forbidden(self):
        self.client.force_login(self.user)
        registrar_group, _ = Group.objects.get_or_create(name="registrar")
        self.user.groups.add(registrar_group)
        response = self.client.get(reverse("frontend:role-home-detail", kwargs={"role_key": "cashier"}))
        self.assertEqual(response.status_code, 403)

    def test_owners_view_requires_permission(self):
        self.client.force_login(self.user)
        forbidden = self.client.get(reverse("frontend:owners-list"))
        self.assertEqual(forbidden.status_code, 403)

        view_owner = Permission.objects.get(codename="view_owner")
        self.user.user_permissions.add(view_owner)
        allowed = self.client.get(reverse("frontend:owners-list"))
        self.assertEqual(allowed.status_code, 200)

    def test_role_cabinets_page_for_assigned_role(self):
        self.client.force_login(self.user)
        registrar_group, _ = Group.objects.get_or_create(name="registrar")
        self.user.groups.add(registrar_group)
        response = self.client.get(reverse("frontend:role-cabinets"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Кабинеты по ролям")

    def test_documents_board_permission_control(self):
        self.client.force_login(self.user)
        denied = self.client.get(reverse("frontend:documents-board"))
        self.assertEqual(denied.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_clinicaldocument"))
        allowed = self.client.get(reverse("frontend:documents-board"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Документы и медиа")

    def test_hospitalization_board_permission_control(self):
        self.client.force_login(self.user)
        denied = self.client.get(reverse("frontend:hospitalization-board"))
        self.assertEqual(denied.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_hospitalization"))
        allowed = self.client.get(reverse("frontend:hospitalization-board"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Стационар")

    def test_mar_board_permission_control(self):
        self.client.force_login(self.user)
        denied = self.client.get(reverse("frontend:mar-board"))
        self.assertEqual(denied.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_medicationadministration"))
        allowed = self.client.get(reverse("frontend:mar-board"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Medication Administration Record")

    def test_finance_board_permission_control(self):
        self.client.force_login(self.user)
        denied = self.client.get(reverse("frontend:finance-board"))
        self.assertEqual(denied.status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_invoice"))
        allowed = self.client.get(reverse("frontend:finance-board"))
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Финансовый кабинет")
