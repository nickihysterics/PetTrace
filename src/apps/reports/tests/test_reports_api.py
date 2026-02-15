from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.labs.models import LabOrder
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class ReportsApiTests(APITestCase):
    def setUp(self):
        owner = Owner.objects.create(
            first_name="Pavel",
            last_name="Mikhailov",
            phone="+79991230003",
        )
        pet = Pet.objects.create(
            owner=owner,
            name="Luna",
            species=Pet.Species.CAT,
            microchip_id="900000000000103",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        LabOrder.objects.create(visit=visit, status=LabOrder.LabOrderStatus.PLANNED)

        user_model = get_user_model()
        self.lab_user = user_model.objects.create_user(
            email="lab.reports@pettrace.local",
            password="test",
        )
        self.assistant = user_model.objects.create_user(
            email="assistant.reports@pettrace.local",
            password="test",
        )

        self._grant_perm(self.lab_user, "labs", "view_laborder")
        self._grant_perm(self.lab_user, "labs", "view_labtest")
        self._grant_perm(self.lab_user, "labs", "view_specimen")

    def _grant_perm(self, user, app_label: str, codename: str):
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        user.user_permissions.add(perm)

    def test_labs_turnaround_report_returns_expected_payload(self):
        self.client.force_authenticate(self.lab_user)

        response = self.client.get("/api/reports/labs/turnaround/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("date_from", response.data)
        self.assertIn("date_to", response.data)
        self.assertIn("generated_at", response.data)
        self.assertIn("total_orders", response.data)
        self.assertIn("status_breakdown", response.data)

    def test_report_with_invalid_date_returns_400(self):
        self.client.force_authenticate(self.lab_user)

        response = self.client.get("/api/reports/labs/turnaround/?date_from=not-a-date")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid date_from", response.data["detail"])

    def test_finance_report_without_permissions_returns_403(self):
        self.client.force_authenticate(self.assistant)

        response = self.client.get("/api/reports/finance/summary/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_labs_report_can_be_exported_to_csv(self):
        self.client.force_authenticate(self.lab_user)

        response = self.client.get("/api/reports/labs/turnaround/?export=csv")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        csv_text = response.content.decode("utf-8")
        self.assertIn("total_orders", csv_text)

    def test_labs_report_cache_hit_and_invalidation(self):
        self.client.force_authenticate(self.lab_user)

        first = self.client.get("/api/reports/labs/turnaround/")
        second = self.client.get("/api/reports/labs/turnaround/")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["generated_at"], second.data["generated_at"])

        total_before = second.data["total_orders"]
        visit = Visit.objects.first()
        LabOrder.objects.create(visit=visit, status=LabOrder.LabOrderStatus.PLANNED)

        third = self.client.get("/api/reports/labs/turnaround/")
        self.assertEqual(third.status_code, status.HTTP_200_OK)
        self.assertEqual(third.data["total_orders"], total_before + 1)
        self.assertNotEqual(third.data["generated_at"], second.data["generated_at"])

    def test_refresh_true_bypasses_cache(self):
        self.client.force_authenticate(self.lab_user)

        cached = self.client.get("/api/reports/labs/turnaround/")
        refreshed = self.client.get("/api/reports/labs/turnaround/?refresh=true")

        self.assertEqual(cached.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertNotEqual(cached.data["generated_at"], refreshed.data["generated_at"])
