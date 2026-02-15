from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DiscountRuleViewSet,
    InvoiceLineViewSet,
    InvoiceViewSet,
    PaymentAdjustmentViewSet,
    PaymentViewSet,
    PriceItemViewSet,
)

router = DefaultRouter()
router.register("price-items", PriceItemViewSet, basename="price-item")
router.register("discount-rules", DiscountRuleViewSet, basename="discount-rule")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-lines", InvoiceLineViewSet, basename="invoice-line")
router.register("payments", PaymentViewSet, basename="payment")
router.register("payment-adjustments", PaymentAdjustmentViewSet, basename="payment-adjustment")

urlpatterns = [
    path("", include(router.urls)),
]
