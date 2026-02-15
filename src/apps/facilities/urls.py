from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BranchViewSet,
    CabinetViewSet,
    EquipmentTypeViewSet,
    EquipmentViewSet,
    HospitalBedViewSet,
    HospitalWardViewSet,
    OrganizationViewSet,
    ServiceRequirementEquipmentViewSet,
    ServiceRequirementViewSet,
    ServiceViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("branches", BranchViewSet, basename="branch")
router.register("cabinets", CabinetViewSet, basename="cabinet")
router.register("equipment-types", EquipmentTypeViewSet, basename="equipment-type")
router.register("equipment", EquipmentViewSet, basename="equipment")
router.register("services", ServiceViewSet, basename="service")
router.register("service-requirements", ServiceRequirementViewSet, basename="service-requirement")
router.register(
    "service-requirement-equipment",
    ServiceRequirementEquipmentViewSet,
    basename="service-requirement-equipment",
)
router.register("hospital-wards", HospitalWardViewSet, basename="hospital-ward")
router.register("hospital-beds", HospitalBedViewSet, basename="hospital-bed")

urlpatterns = [
    path("", include(router.urls)),
]
