from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ContainerLabelViewSet,
    LabOrderViewSet,
    LabParameterReferenceViewSet,
    LabResultValueViewSet,
    LabTestViewSet,
    SpecimenEventViewSet,
    SpecimenRecollectionViewSet,
    SpecimenTubeViewSet,
    SpecimenViewSet,
    TubeViewSet,
)

router = DefaultRouter()
router.register("orders", LabOrderViewSet, basename="lab-order")
router.register("tests", LabTestViewSet, basename="lab-test")
router.register("specimens", SpecimenViewSet, basename="specimen")
router.register("tubes", TubeViewSet, basename="tube")
router.register("specimen-tubes", SpecimenTubeViewSet, basename="specimen-tube")
router.register("labels", ContainerLabelViewSet, basename="container-label")
router.register("events", SpecimenEventViewSet, basename="specimen-event")
router.register("recollections", SpecimenRecollectionViewSet, basename="specimen-recollection")
router.register("parameter-references", LabParameterReferenceViewSet, basename="lab-parameter-reference")
router.register("results", LabResultValueViewSet, basename="lab-result")

urlpatterns = [
    path("", include(router.urls)),
]
