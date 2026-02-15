from django.contrib import admin

from .models import (
    Branch,
    Cabinet,
    Equipment,
    EquipmentType,
    HospitalBed,
    HospitalWard,
    Organization,
    Service,
    ServiceRequirement,
    ServiceRequirementEquipment,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["id", "organization", "code", "name", "phone", "is_active"]
    list_filter = ["organization", "is_active"]
    search_fields = ["code", "name", "address"]


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ["id", "branch", "code", "name", "cabinet_type", "capacity", "is_active"]
    list_filter = ["branch", "cabinet_type", "is_active"]
    search_fields = ["code", "name", "branch__code", "branch__name"]


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "equipment_type", "branch", "cabinet", "status", "is_active"]
    list_filter = ["branch", "equipment_type", "status", "is_active"]
    search_fields = ["code", "name", "equipment_type__code"]


@admin.register(ServiceRequirement)
class ServiceRequirementAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "service",
        "service_type",
        "required_cabinet_type",
        "default_duration_minutes",
        "is_active",
    ]
    list_filter = ["required_cabinet_type", "is_active"]
    search_fields = ["service_type", "description"]


@admin.register(ServiceRequirementEquipment)
class ServiceRequirementEquipmentAdmin(admin.ModelAdmin):
    list_display = ["id", "requirement", "equipment_type", "quantity"]
    list_filter = ["requirement"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "category", "default_duration_minutes", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["code", "name"]


@admin.register(HospitalWard)
class HospitalWardAdmin(admin.ModelAdmin):
    list_display = ["id", "branch", "code", "name", "is_active"]
    list_filter = ["branch", "is_active"]
    search_fields = ["code", "name", "branch__code"]


@admin.register(HospitalBed)
class HospitalBedAdmin(admin.ModelAdmin):
    list_display = ["id", "ward", "code", "cabinet", "status", "is_isolation", "is_active"]
    list_filter = ["ward", "status", "is_isolation", "is_active"]
    search_fields = ["code", "ward__code", "ward__branch__code"]
