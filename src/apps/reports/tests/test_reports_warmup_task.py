from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.labs.models import LabOrder
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.reports.cache import build_report_cache_key
from apps.reports.tasks import warm_reports_cache
from apps.visits.models import Visit


class ReportsWarmupTaskTests(TestCase):
    def setUp(self):
        cache.clear()
        owner = Owner.objects.create(
            first_name="Warm",
            last_name="Up",
            phone="+79991230030",
        )
        pet = Pet.objects.create(
            owner=owner,
            name="Cache",
            species=Pet.Species.CAT,
            microchip_id="900000000000130",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        LabOrder.objects.create(
            visit=visit,
            status=LabOrder.LabOrderStatus.PLANNED,
        )

    @override_settings(REPORTS_WARMUP_DAYS=[1])
    def test_warmup_populates_cache_for_one_window(self):
        result = warm_reports_cache()

        self.assertEqual(result["windows"], [1])
        self.assertEqual(result["reports"], 4)
        self.assertEqual(result["entries"], 4)

        today = timezone.localdate().isoformat()
        params = {"date_from": today, "date_to": today}
        key = build_report_cache_key("labs-turnaround", params, ("labs",))
        payload = cache.get(key)

        self.assertIsNotNone(payload)
        self.assertIn("total_orders", payload)

    @override_settings(REPORTS_WARMUP_DAYS=["bad", "-1", "0"])
    def test_invalid_warmup_days_fallback_to_defaults(self):
        result = warm_reports_cache()

        self.assertEqual(result["windows"], [1, 7, 30])
        self.assertEqual(result["reports"], 4)
        self.assertEqual(result["entries"], 12)
