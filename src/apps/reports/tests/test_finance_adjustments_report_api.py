from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing.models import Invoice, Payment, PaymentAdjustment
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class FinanceAdjustmentsReportApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.finance.report@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Fin", last_name="Report", phone="+79990004001")
        pet = Pet.objects.create(
            owner=owner,
            name="FinancePet",
            species=Pet.Species.DOG,
            microchip_id="900000000004001",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.COMPLETED,
        )
        self.invoice = Invoice.objects.create(
            visit=visit,
            status=Invoice.InvoiceStatus.POSTED,
            subtotal_amount=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        payment = Payment.objects.create(
            invoice=self.invoice,
            method=Payment.PaymentMethod.CARD,
            amount=Decimal("100.00"),
        )
        PaymentAdjustment.objects.create(
            payment=payment,
            adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
            amount=Decimal("10.00"),
            reason="Partial refund",
        )
        PaymentAdjustment.objects.create(
            payment=payment,
            adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
            amount=Decimal("2.00"),
            reason="Terminal correction",
        )

    def test_finance_summary_includes_net_paid_metrics(self):
        response = self.client.get("/api/reports/finance/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Decimal(response.data["paid_amount"]), Decimal("100.00"))
        self.assertEqual(Decimal(response.data["refund_amount"]), Decimal("10.00"))
        self.assertEqual(Decimal(response.data["correction_amount"]), Decimal("2.00"))
        self.assertEqual(Decimal(response.data["net_paid_amount"]), Decimal("92.00"))
