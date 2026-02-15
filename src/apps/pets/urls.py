from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PetAttachmentViewSet, PetViewSet

router = DefaultRouter()
router.register("pets", PetViewSet, basename="pet")
router.register("attachments", PetAttachmentViewSet, basename="pet-attachment")

urlpatterns = [
    path("", include(router.urls)),
]
