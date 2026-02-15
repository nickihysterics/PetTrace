from django.contrib import admin

from .models import (
    Appointment,
    AppointmentQueueCounter,
    Diagnosis,
    HospitalBedStay,
    Hospitalization,
    HospitalProcedurePlan,
    HospitalVitalRecord,
    MedicationAdministration,
    Observation,
    Prescription,
    ProcedureOrder,
    Visit,
    VisitEvent,
)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ["id", "pet", "owner", "status", "branch", "cabinet", "veterinarian", "scheduled_at"]
    list_filter = ["status", "branch", "cabinet", "scheduled_at"]
    search_fields = ["pet__name", "owner__phone", "owner__last_name"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "pet",
        "owner",
        "status",
        "branch",
        "cabinet",
        "veterinarian",
        "start_at",
        "queue_number",
        "room",
    ]
    list_filter = ["status", "branch", "cabinet", "start_at", "veterinarian"]
    search_fields = ["pet__name", "owner__phone", "owner__last_name", "service_type", "service__code", "service__name"]


@admin.register(AppointmentQueueCounter)
class AppointmentQueueCounterAdmin(admin.ModelAdmin):
    list_display = ["id", "queue_date", "veterinarian", "last_number", "updated_at"]
    list_filter = ["queue_date", "veterinarian"]
    search_fields = ["veterinarian__email"]


@admin.register(VisitEvent)
class VisitEventAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "from_status", "to_status", "actor", "event_at"]
    list_filter = ["to_status"]
    search_fields = ["visit__id", "actor__email", "notes"]


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "title", "is_primary"]
    list_filter = ["is_primary"]
    search_fields = ["title", "code"]


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "name", "value", "unit"]
    search_fields = ["name", "value"]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "medication_name", "duration_days"]
    search_fields = ["medication_name"]


@admin.register(ProcedureOrder)
class ProcedureOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "name", "status", "performed_by"]
    list_filter = ["status"]
    search_fields = ["name"]


@admin.register(Hospitalization)
class HospitalizationAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "status", "branch", "cabinet", "admitted_at", "discharged_at", "cage_number"]
    list_filter = ["status", "branch", "cabinet"]
    search_fields = ["visit__pet__name", "visit__owner__phone", "cage_number", "care_plan"]


@admin.register(HospitalBedStay)
class HospitalBedStayAdmin(admin.ModelAdmin):
    list_display = ["id", "hospitalization", "bed", "moved_in_at", "moved_out_at", "is_current", "moved_by"]
    list_filter = ["is_current", "bed__ward", "bed__ward__branch"]
    search_fields = ["hospitalization__visit__pet__name", "bed__code", "notes"]


@admin.register(HospitalVitalRecord)
class HospitalVitalRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "hospitalization", "measured_at", "temperature_c", "pulse_bpm", "respiratory_rate", "recorded_by"]
    list_filter = ["appetite_status", "hospitalization__branch"]
    search_fields = ["hospitalization__visit__pet__name", "notes"]


@admin.register(HospitalProcedurePlan)
class HospitalProcedurePlanAdmin(admin.ModelAdmin):
    list_display = ["id", "hospitalization", "title", "scheduled_at", "status", "completed_by", "completed_at"]
    list_filter = ["status", "hospitalization__branch"]
    search_fields = ["title", "instructions", "notes"]


@admin.register(MedicationAdministration)
class MedicationAdministrationAdmin(admin.ModelAdmin):
    list_display = ["id", "prescription", "scheduled_at", "status", "dose_amount", "dose_unit", "given_by", "given_at"]
    list_filter = ["status", "route", "given_by"]
    search_fields = ["prescription__medication_name", "deviation_note", "write_off_note"]
