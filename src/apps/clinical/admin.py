from django.contrib import admin

from .models import (
    ClinicalAlert,
    ClinicalProtocol,
    ContraindicationRule,
    DiagnosisCatalog,
    ProcedureChecklist,
    ProcedureChecklistItem,
    ProcedureChecklistTemplate,
    ProcedureChecklistTemplateItem,
    ProtocolMedicationTemplate,
    ProtocolProcedureTemplate,
    SymptomCatalog,
)


@admin.register(ClinicalProtocol)
class ClinicalProtocolAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "diagnosis_code", "species", "is_active"]
    list_filter = ["species", "is_active"]
    search_fields = ["name", "diagnosis_code", "diagnosis_title"]


@admin.register(DiagnosisCatalog)
class DiagnosisCatalogAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "title", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "title", "description"]


@admin.register(SymptomCatalog)
class SymptomCatalogAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]


@admin.register(ProtocolMedicationTemplate)
class ProtocolMedicationTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "protocol", "medication_name", "dose_mg_per_kg", "fixed_dose_mg", "duration_days"]
    list_filter = ["protocol"]
    search_fields = ["protocol__name", "medication_name"]


@admin.register(ProtocolProcedureTemplate)
class ProtocolProcedureTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "protocol", "name"]
    list_filter = ["protocol"]
    search_fields = ["protocol__name", "name"]


@admin.register(ContraindicationRule)
class ContraindicationRuleAdmin(admin.ModelAdmin):
    list_display = ["id", "medication_name", "allergy_keyword", "species", "severity", "is_active"]
    list_filter = ["species", "severity", "is_active"]
    search_fields = ["medication_name", "allergy_keyword", "message"]


@admin.register(ClinicalAlert)
class ClinicalAlertAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "prescription", "severity", "resolved_at", "resolved_by"]
    list_filter = ["severity", "resolved_at"]
    search_fields = ["visit__id", "prescription__medication_name", "message"]


@admin.register(ProcedureChecklistTemplate)
class ProcedureChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "procedure_name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "procedure_name"]


@admin.register(ProcedureChecklistTemplateItem)
class ProcedureChecklistTemplateItemAdmin(admin.ModelAdmin):
    list_display = ["id", "template", "title", "is_required", "sort_order"]
    list_filter = ["template", "is_required"]
    search_fields = ["title", "template__name"]


@admin.register(ProcedureChecklist)
class ProcedureChecklistAdmin(admin.ModelAdmin):
    list_display = ["id", "procedure_order", "template", "status", "started_at", "completed_at"]
    list_filter = ["status", "template"]


@admin.register(ProcedureChecklistItem)
class ProcedureChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["id", "checklist", "title", "is_required", "is_completed", "completed_by"]
    list_filter = ["is_required", "is_completed"]
    search_fields = ["title", "checklist__id"]
