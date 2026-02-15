from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import decorators, response, status
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.services import get_setting_bool
from apps.common.viewsets import RBACModelViewSet, RBACReadOnlyModelViewSet
from apps.users.access import ensure_user_can_access_branch_cabinet
from apps.visits.models import Visit, VisitEvent

from .models import DiscountRule, Invoice, InvoiceLine, Payment, PaymentAdjustment, PriceItem
from .serializers import (
    DiscountRuleSerializer,
    InvoiceLineSerializer,
    InvoiceSerializer,
    PaymentAdjustmentSerializer,
    PaymentSerializer,
    PriceItemSerializer,
)


def _sum_payments(invoice: Invoice) -> Decimal:
    total = Payment.objects.filter(invoice=invoice).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return total


def _sum_adjustments(invoice: Invoice) -> tuple[Decimal, Decimal]:
    refunds = (
        PaymentAdjustment.objects.filter(
            payment__invoice=invoice,
            adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    corrections = (
        PaymentAdjustment.objects.filter(
            payment__invoice=invoice,
            adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    return refunds, corrections


def _sum_payment_adjustments(payment: Payment) -> tuple[Decimal, Decimal]:
    refunds = (
        PaymentAdjustment.objects.filter(
            payment=payment,
            adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    corrections = (
        PaymentAdjustment.objects.filter(
            payment=payment,
            adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    return refunds, corrections


def _invoice_net_paid(invoice: Invoice) -> Decimal:
    paid_total = _sum_payments(invoice)
    refunds, corrections = _sum_adjustments(invoice)
    return paid_total - refunds + corrections


def _invoice_remaining_amount(invoice: Invoice) -> Decimal:
    remaining = invoice.total_amount - _invoice_net_paid(invoice)
    return max(remaining, Decimal("0"))


def _sync_invoice_payment_status(*, invoice: Invoice, actor=None) -> Invoice:
    net_paid = _invoice_net_paid(invoice)

    if net_paid >= invoice.total_amount and invoice.total_amount > 0:
        if invoice.status != Invoice.InvoiceStatus.PAID:
            invoice.status = Invoice.InvoiceStatus.PAID
            invoice.save(update_fields=["status", "updated_at"])

            visit = invoice.visit
            auto_close_visit = get_setting_bool("visit.auto_close_on_payment", default=True)
            if auto_close_visit and visit.status == Visit.VisitStatus.COMPLETED:
                previous = visit.status
                visit.transition_to(Visit.VisitStatus.CLOSED)
                visit.save(update_fields=["status", "ended_at", "updated_at"])
                VisitEvent.objects.create(
                    visit=visit,
                    from_status=previous,
                    to_status=visit.status,
                    actor=actor,
                    notes=f"Visit auto-closed after payment for invoice #{invoice.id}",
                )
        return invoice

    if invoice.status == Invoice.InvoiceStatus.PAID:
        invoice.status = Invoice.InvoiceStatus.POSTED
        invoice.save(update_fields=["status", "updated_at"])
    return invoice


def _resolve_discount_rule(invoice: Invoice, *, promo_code: str = "", rule_id: int | None = None) -> DiscountRule | None:
    if rule_id:
        return DiscountRule.objects.filter(id=rule_id, is_active=True).first()

    visit_owner = getattr(invoice.visit, "owner", None)
    if promo_code:
        return DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.PROMO,
            promo_code__iexact=promo_code,
        ).first()

    owner_rule = None
    if visit_owner:
        owner_rule = DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.OWNER,
            owner=visit_owner,
            auto_apply=True,
        ).first()
    if owner_rule:
        return owner_rule

    if visit_owner:
        owner_tag_ids = visit_owner.tag_assignments.values_list("tag_id", flat=True)
        tag_rule = DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.OWNER_TAG,
            owner_tag_id__in=owner_tag_ids,
            auto_apply=True,
        ).first()
        if tag_rule:
            return tag_rule

    return DiscountRule.objects.filter(
        is_active=True,
        scope=DiscountRule.RuleScope.GLOBAL,
        auto_apply=True,
    ).first()


def _ensure_invoice_mutable(invoice: Invoice) -> None:
    if invoice.status in {
        Invoice.InvoiceStatus.POSTED,
        Invoice.InvoiceStatus.PAID,
        Invoice.InvoiceStatus.CANCELED,
    }:
        raise DRFValidationError(
            f"invoice in status {invoice.status} is not editable"
        )


class PriceItemViewSet(RBACModelViewSet):
    queryset = PriceItem.objects.all()
    serializer_class = PriceItemSerializer
    filterset_fields = ["is_active", "currency"]
    search_fields = ["code", "name"]


class DiscountRuleViewSet(RBACModelViewSet):
    queryset = DiscountRule.objects.select_related("owner", "owner_tag").all()
    serializer_class = DiscountRuleSerializer
    filterset_fields = ["scope", "discount_type", "owner", "owner_tag", "auto_apply", "is_active"]
    search_fields = ["code", "name", "promo_code"]


class InvoiceViewSet(RBACModelViewSet):
    queryset = Invoice.objects.select_related("visit", "applied_discount_rule").prefetch_related("lines", "payments").all()
    serializer_class = InvoiceSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["status", "visit", "applied_discount_rule"]
    search_fields = ["visit__pet__name", "visit__owner__phone", "discount_code"]

    def perform_create(self, serializer):
        visit = serializer.validated_data.get("visit")
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        visit = serializer.validated_data.get("visit", serializer.instance.visit)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="recalculate")
    @transaction.atomic
    def recalculate(self, request, pk=None):
        invoice = self.get_object()
        _ensure_invoice_mutable(invoice)
        invoice.recalculate_totals()
        invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
        return response.Response(self.get_serializer(invoice).data)

    @decorators.action(detail=True, methods=["post"], url_path="apply-discount")
    @transaction.atomic
    def apply_discount(self, request, pk=None):
        invoice = self.get_object()
        _ensure_invoice_mutable(invoice)
        rule_id = request.data.get("rule")
        promo_code = (request.data.get("promo_code") or "").strip()

        rule = _resolve_discount_rule(invoice, promo_code=promo_code, rule_id=rule_id)
        invoice.recalculate_totals()
        if rule is None:
            invoice.applied_discount_rule = None
            invoice.discount_amount = Decimal("0")
            invoice.discount_code = promo_code
            invoice.recalculate_totals()
            invoice.save(
                update_fields=[
                    "applied_discount_rule",
                    "discount_amount",
                    "discount_code",
                    "subtotal_amount",
                    "total_amount",
                    "updated_at",
                ]
            )
            return response.Response(self.get_serializer(invoice).data)

        discount_amount = rule.calculate_discount_amount(invoice.subtotal_amount)
        invoice.applied_discount_rule = rule
        invoice.discount_amount = discount_amount
        invoice.discount_code = promo_code or rule.promo_code
        invoice.recalculate_totals()
        invoice.save(
            update_fields=[
                "applied_discount_rule",
                "discount_amount",
                "discount_code",
                "subtotal_amount",
                "total_amount",
                "updated_at",
            ]
        )
        return response.Response(self.get_serializer(invoice).data)

    @decorators.action(detail=True, methods=["post"], url_path="form")
    @transaction.atomic
    def form(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.InvoiceStatus.CANCELED:
            return response.Response(
                {"detail": "cannot form canceled invoice"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.recalculate_totals()
        if invoice.status == Invoice.InvoiceStatus.DRAFT:
            invoice.status = Invoice.InvoiceStatus.FORMED
        if invoice.formed_at is None:
            invoice.formed_at = timezone.now()
        invoice.save(
            update_fields=["subtotal_amount", "total_amount", "status", "formed_at", "updated_at"]
        )
        return response.Response(self.get_serializer(invoice).data)

    @decorators.action(detail=True, methods=["post"], url_path="issue")
    @transaction.atomic
    def issue(self, request, pk=None):
        return self.form(request, pk=pk)

    @decorators.action(detail=True, methods=["post"], url_path="post")
    @transaction.atomic
    def post_invoice(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status in {Invoice.InvoiceStatus.CANCELED, Invoice.InvoiceStatus.PAID}:
            return response.Response(
                {"detail": f"cannot post invoice in status {invoice.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.recalculate_totals()
        if invoice.status == Invoice.InvoiceStatus.DRAFT:
            invoice.status = Invoice.InvoiceStatus.FORMED
        invoice.status = Invoice.InvoiceStatus.POSTED
        if invoice.formed_at is None:
            invoice.formed_at = timezone.now()
        if invoice.posted_at is None:
            invoice.posted_at = timezone.now()
        invoice.save(
            update_fields=[
                "subtotal_amount",
                "total_amount",
                "status",
                "formed_at",
                "posted_at",
                "updated_at",
            ]
        )
        return response.Response(self.get_serializer(invoice).data)

    @decorators.action(detail=True, methods=["post"], url_path="pay")
    @transaction.atomic
    def pay(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status not in {
            Invoice.InvoiceStatus.FORMED,
            Invoice.InvoiceStatus.POSTED,
            Invoice.InvoiceStatus.PAID,
        }:
            return response.Response(
                {"detail": "invoice must be FORMED or POSTED before payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except (InvalidOperation, TypeError):
            return response.Response({"detail": "amount must be a number"}, status=status.HTTP_400_BAD_REQUEST)
        method = request.data.get("method")

        if amount <= 0 or not method:
            return response.Response({"detail": "amount and method are required"}, status=status.HTTP_400_BAD_REQUEST)
        if invoice.total_amount <= 0:
            return response.Response(
                {"detail": "invoice total amount must be positive before payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allow_overpayment = get_setting_bool("billing.allow_overpayment", default=False)
        remaining_amount = _invoice_remaining_amount(invoice)
        if not allow_overpayment and amount > remaining_amount:
            return response.Response(
                {
                    "detail": (
                        "payment exceeds outstanding amount; "
                        f"remaining={remaining_amount}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.create(
            invoice=invoice,
            method=method,
            amount=amount,
            external_id=request.data.get("external_id", ""),
        )
        _sync_invoice_payment_status(
            invoice=invoice,
            actor=request.user if request.user.is_authenticated else None,
        )
        return response.Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class InvoiceLineViewSet(RBACModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice", "price_item").all()
    serializer_class = InvoiceLineSerializer
    scope_branch_field = "invoice__visit__branch"
    scope_cabinet_field = "invoice__visit__cabinet"
    filterset_fields = ["invoice", "price_item", "is_void"]
    search_fields = ["description", "void_reason"]

    def perform_create(self, serializer):
        invoice = serializer.validated_data.get("invoice")
        _ensure_invoice_mutable(invoice)
        visit = getattr(invoice, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        line = serializer.save()
        invoice.recalculate_totals()
        invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
        return line

    def perform_update(self, serializer):
        invoice = serializer.validated_data.get("invoice", serializer.instance.invoice)
        _ensure_invoice_mutable(invoice)
        visit = getattr(invoice, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()
        invoice.recalculate_totals()
        invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])

    @decorators.action(detail=True, methods=["post"], url_path="void")
    @transaction.atomic
    def void(self, request, pk=None):
        line = self.get_object()
        _ensure_invoice_mutable(line.invoice)
        line.is_void = True
        line.void_reason = request.data.get("reason", "")
        line.save(update_fields=["is_void", "void_reason", "updated_at"])

        invoice = line.invoice
        invoice.recalculate_totals()
        invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
        return response.Response(self.get_serializer(line).data)


class PaymentViewSet(RBACReadOnlyModelViewSet):
    queryset = Payment.objects.select_related("invoice").all()
    serializer_class = PaymentSerializer
    scope_branch_field = "invoice__visit__branch"
    scope_cabinet_field = "invoice__visit__cabinet"
    filterset_fields = ["invoice", "method"]
    search_fields = ["external_id"]

    @decorators.action(detail=True, methods=["post"], url_path="adjust")
    @transaction.atomic
    def adjust(self, request, pk=None):
        payment = self.get_object()
        adjustment_type = request.data.get("adjustment_type")
        reason = (request.data.get("reason") or "").strip()
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except (InvalidOperation, TypeError):
            return response.Response({"detail": "amount must be a number"}, status=status.HTTP_400_BAD_REQUEST)

        if not reason:
            return response.Response({"detail": "reason is required"}, status=status.HTTP_400_BAD_REQUEST)
        if adjustment_type not in {
            PaymentAdjustment.AdjustmentType.REFUND,
            PaymentAdjustment.AdjustmentType.CORRECTION,
        }:
            return response.Response({"detail": "invalid adjustment_type"}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return response.Response({"detail": "amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        if adjustment_type == PaymentAdjustment.AdjustmentType.REFUND:
            refunds, corrections = _sum_payment_adjustments(payment)
            max_refundable = payment.amount + corrections - refunds
            if amount > max_refundable:
                return response.Response(
                    {
                        "detail": (
                            "refund exceeds available refundable amount; "
                            f"max_refundable={max_refundable}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        adjustment = PaymentAdjustment.objects.create(
            payment=payment,
            adjustment_type=adjustment_type,
            amount=amount,
            reason=reason,
            adjusted_by=request.user if request.user.is_authenticated else None,
            external_reference=request.data.get("external_reference", ""),
        )
        _sync_invoice_payment_status(
            invoice=payment.invoice,
            actor=request.user if request.user.is_authenticated else None,
        )
        return response.Response(PaymentAdjustmentSerializer(adjustment).data, status=status.HTTP_201_CREATED)


class PaymentAdjustmentViewSet(RBACReadOnlyModelViewSet):
    queryset = PaymentAdjustment.objects.select_related("payment", "payment__invoice", "adjusted_by").all()
    serializer_class = PaymentAdjustmentSerializer
    scope_branch_field = "payment__invoice__visit__branch"
    scope_cabinet_field = "payment__invoice__visit__cabinet"
    filterset_fields = ["payment", "adjustment_type", "adjusted_by"]
    search_fields = ["reason", "external_reference"]
