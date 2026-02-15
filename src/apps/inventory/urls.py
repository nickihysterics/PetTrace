from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BatchViewSet, InventoryItemViewSet, StockMovementViewSet

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="inventory-item")
router.register("batches", BatchViewSet, basename="inventory-batch")
router.register("movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = [
    path("", include(router.urls)),
]
