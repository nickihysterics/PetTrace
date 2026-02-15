from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    DiagnosisViewSet,
    HospitalBedStayViewSet,
    HospitalizationViewSet,
    HospitalProcedurePlanViewSet,
    HospitalVitalRecordViewSet,
    MedicationAdministrationViewSet,
    ObservationViewSet,
    PrescriptionViewSet,
    ProcedureOrderViewSet,
    VisitEventViewSet,
    VisitViewSet,
)

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("encounters", VisitViewSet, basename="visit")
router.register("visit-events", VisitEventViewSet, basename="visit-event")
router.register("hospitalizations", HospitalizationViewSet, basename="hospitalization")
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("observations", ObservationViewSet, basename="observation")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("medication-administrations", MedicationAdministrationViewSet, basename="medication-administration")
router.register("procedures", ProcedureOrderViewSet, basename="procedure-order")
router.register("hospital-bed-stays", HospitalBedStayViewSet, basename="hospital-bed-stay")
router.register("hospital-vitals", HospitalVitalRecordViewSet, basename="hospital-vital")
router.register("hospital-procedure-plans", HospitalProcedurePlanViewSet, basename="hospital-procedure-plan")

urlpatterns = [
    path("", include(router.urls)),
]
