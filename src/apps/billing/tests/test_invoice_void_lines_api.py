from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing.models import Invoice, InvoiceLine
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.visits.models import Visit


class InvoiceVoidLinesApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.billing@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        owner = Owner.objects.create(first_name="Bill", last_name="Owner", phone="+79990002001")
        pet = Pet.objects.create(
            owner=owner,
            name="Bolt",
            species=Pet.Species.DOG,
            microchip_id="900000000002001",
        )
        visit = Visit.objects.create(
            pet=pet,
            owner=owner,
            status=Visit.VisitStatus.IN_PROGRESS,
        )
        self.invoice = Invoice.objects.create(visit=visit)
        self.line_primary = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Consultation",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
        )
        self.line_voidable = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Procedure",
            quantity=Decimal("2"),
            unit_price=Decimal("10.00"),
        )

    def test_voided_line_is_excluded_from_invoice_totals(self):
        recalculate = self.client.post(f"/api/invoices/{self.invoice.id}/recalculate/")
        self.assertEqual(recalculate.status_code, status.HTTP_200_OK)
        self.assertEqual(recalculate.data["subtotal_amount"], "30.00")
        self.assertEqual(recalculate.data["total_amount"], "30.00")

        void_response = self.client.post(
            f"/api/invoice-lines/{self.line_voidable.id}/void/",
            {"reason": "Canceled by client"},
            format="json",
        )
        self.assertEqual(void_response.status_code, status.HTTP_200_OK)
        self.assertTrue(void_response.data["is_void"])

        self.invoice.refresh_from_db()
        self.assertEqual(str(self.invoice.subtotal_amount), "10.00")
        self.assertEqual(str(self.invoice.total_amount), "10.00")

        recalculate_after_void = self.client.post(f"/api/invoices/{self.invoice.id}/recalculate/")
        self.assertEqual(recalculate_after_void.status_code, status.HTTP_200_OK)
        self.assertEqual(recalculate_after_void.data["subtotal_amount"], "10.00")
        self.assertEqual(recalculate_after_void.data["total_amount"], "10.00")

    def test_payment_cannot_exceed_outstanding_amount_by_default(self):
        self.client.post(f"/api/invoices/{self.invoice.id}/post/")

        overpayment = self.client.post(
            f"/api/invoices/{self.invoice.id}/pay/",
            {"amount": "31.00", "method": "CASH"},
            format="json",
        )
        self.assertEqual(overpayment.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds outstanding amount", overpayment.data["detail"])

    def test_refund_cannot_exceed_payment_net_amount(self):
        self.client.post(f"/api/invoices/{self.invoice.id}/post/")
        payment = self.client.post(
            f"/api/invoices/{self.invoice.id}/pay/",
            {"amount": "30.00", "method": "CARD"},
            format="json",
        )
        self.assertEqual(payment.status_code, status.HTTP_201_CREATED)
        payment_id = payment.data["id"]

        first_refund = self.client.post(
            f"/api/payments/{payment_id}/adjust/",
            {
                "adjustment_type": "REFUND",
                "amount": "20.00",
                "reason": "partial refund",
            },
            format="json",
        )
        self.assertEqual(first_refund.status_code, status.HTTP_201_CREATED)

        excessive_refund = self.client.post(
            f"/api/payments/{payment_id}/adjust/",
            {
                "adjustment_type": "REFUND",
                "amount": "15.00",
                "reason": "too much refund",
            },
            format="json",
        )
        self.assertEqual(excessive_refund.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refund exceeds available refundable amount", excessive_refund.data["detail"])

    def test_invoice_line_requires_positive_quantity(self):
        response = self.client.post(
            "/api/invoice-lines/",
            {
                "invoice": self.invoice.id,
                "description": "Invalid line",
                "quantity": "0",
                "unit_price": "10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_posted_invoice_is_not_editable_for_lines_and_discounts(self):
        self.client.post(f"/api/invoices/{self.invoice.id}/post/")

        add_line = self.client.post(
            "/api/invoice-lines/",
            {
                "invoice": self.invoice.id,
                "description": "Late charge",
                "quantity": "1",
                "unit_price": "5.00",
            },
            format="json",
        )
        self.assertEqual(add_line.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not editable", str(add_line.data))

        apply_discount = self.client.post(
            f"/api/invoices/{self.invoice.id}/apply-discount/",
            {"promo_code": "ANY"},
            format="json",
        )
        self.assertEqual(apply_discount.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not editable", str(apply_discount.data))
