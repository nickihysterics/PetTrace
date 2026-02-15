from django.contrib import admin

from .models import (
    ContainerLabel,
    LabOrder,
    LabParameterReference,
    LabResultValue,
    LabTest,
    Specimen,
    SpecimenEvent,
    SpecimenRecollection,
    SpecimenTube,
    Tube,
)


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "visit", "status", "ordered_by", "ordered_at", "completed_at"]
    list_filter = ["status"]
    search_fields = ["visit__id", "visit__pet__name", "visit__owner__phone"]


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ["id", "lab_order", "code", "name", "status", "specimen_type"]
    list_filter = ["status", "specimen_type"]
    search_fields = ["code", "name"]


@admin.register(Specimen)
class SpecimenAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "lab_order",
        "specimen_type",
        "status",
        "rejection_reason",
        "collected_at",
        "received_at",
    ]
    list_filter = ["status", "specimen_type", "rejection_reason"]
    search_fields = ["lab_order__visit__pet__name", "lab_order__visit__owner__phone"]


@admin.register(Tube)
class TubeAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "tube_type", "lot_number", "expires_at", "inventory_item"]
    list_filter = ["tube_type", "inventory_item"]
    search_fields = ["code", "lot_number", "inventory_item__sku", "inventory_item__name"]


@admin.register(SpecimenTube)
class SpecimenTubeAdmin(admin.ModelAdmin):
    list_display = ["id", "specimen", "tube", "quantity"]


@admin.register(ContainerLabel)
class ContainerLabelAdmin(admin.ModelAdmin):
    list_display = ["id", "specimen", "label_value", "printed_at"]
    search_fields = ["label_value"]


@admin.register(SpecimenEvent)
class SpecimenEventAdmin(admin.ModelAdmin):
    list_display = ["id", "specimen", "from_status", "to_status", "actor", "event_at"]
    list_filter = ["to_status"]


@admin.register(LabResultValue)
class LabResultValueAdmin(admin.ModelAdmin):
    list_display = ["id", "lab_test", "parameter_name", "value", "unit", "flag", "parameter_reference", "source"]
    list_filter = ["flag"]
    search_fields = ["parameter_name", "value"]


@admin.register(SpecimenRecollection)
class SpecimenRecollectionAdmin(admin.ModelAdmin):
    list_display = ["id", "original_specimen", "recollected_specimen", "status", "reason", "requested_by", "requested_at"]
    list_filter = ["status"]
    search_fields = ["reason", "note"]


@admin.register(LabParameterReference)
class LabParameterReferenceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "parameter_name",
        "species",
        "unit",
        "reference_low",
        "reference_high",
        "critical_low",
        "critical_high",
        "is_active",
    ]
    list_filter = ["species", "unit", "is_active"]
    search_fields = ["parameter_name", "note"]
