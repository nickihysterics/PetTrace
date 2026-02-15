from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConsentDocumentViewSet, OwnerViewSet

router = DefaultRouter()
router.register("owners", OwnerViewSet, basename="owner")
router.register("consents", ConsentDocumentViewSet, basename="consent")

urlpatterns = [
    path("", include(router.urls)),
]
