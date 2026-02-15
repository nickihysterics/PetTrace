from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClinicalAlertViewSet,
    ClinicalProtocolViewSet,
    ContraindicationRuleViewSet,
    DiagnosisCatalogViewSet,
    DoseCalculatorView,
    ProcedureChecklistItemViewSet,
    ProcedureChecklistTemplateItemViewSet,
    ProcedureChecklistTemplateViewSet,
    ProcedureChecklistViewSet,
    ProtocolMedicationTemplateViewSet,
    ProtocolProcedureTemplateViewSet,
    SymptomCatalogViewSet,
)

router = DefaultRouter()
router.register("clinical/protocols", ClinicalProtocolViewSet, basename="clinical-protocol")
router.register("clinical/diagnosis-catalog", DiagnosisCatalogViewSet, basename="diagnosis-catalog")
router.register("clinical/symptom-catalog", SymptomCatalogViewSet, basename="symptom-catalog")
router.register("clinical/protocol-medications", ProtocolMedicationTemplateViewSet, basename="protocol-medication")
router.register("clinical/protocol-procedures", ProtocolProcedureTemplateViewSet, basename="protocol-procedure")
router.register("clinical/contraindications", ContraindicationRuleViewSet, basename="contraindication-rule")
router.register("clinical/alerts", ClinicalAlertViewSet, basename="clinical-alert")
router.register("clinical/checklist-templates", ProcedureChecklistTemplateViewSet, basename="checklist-template")
router.register(
    "clinical/checklist-template-items",
    ProcedureChecklistTemplateItemViewSet,
    basename="checklist-template-item",
)
router.register("clinical/checklists", ProcedureChecklistViewSet, basename="procedure-checklist")
router.register("clinical/checklist-items", ProcedureChecklistItemViewSet, basename="procedure-checklist-item")

urlpatterns = [
    path("", include(router.urls)),
    path("clinical/dose-calc/", DoseCalculatorView.as_view(), name="clinical-dose-calc"),
]
