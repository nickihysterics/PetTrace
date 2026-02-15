from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClinicalDocumentViewSet,
    DocumentStoragePolicyViewSet,
    DocumentTemplateViewSet,
    GeneratedDocumentViewSet,
)

router = DefaultRouter()
router.register("documents/storage-policies", DocumentStoragePolicyViewSet, basename="document-storage-policy")
router.register("documents/clinical", ClinicalDocumentViewSet, basename="clinical-document")
router.register("documents/templates", DocumentTemplateViewSet, basename="document-template")
router.register("documents/generated", GeneratedDocumentViewSet, basename="generated-document")

urlpatterns = [
    path("", include(router.urls)),
]
