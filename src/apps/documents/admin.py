from django.contrib import admin

from .models import ClinicalDocument, DocumentStoragePolicy, DocumentTemplate, GeneratedDocument


@admin.register(DocumentStoragePolicy)
class DocumentStoragePolicyAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "storage_backend", "max_file_size_mb", "is_default", "is_active"]
    list_filter = ["storage_backend", "is_default", "is_active"]
    search_fields = ["name"]


@admin.register(ClinicalDocument)
class ClinicalDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "document_uid",
        "version",
        "is_current",
        "document_type",
        "title",
        "visit",
        "pet",
        "lab_order",
        "uploaded_by",
    ]
    list_filter = ["document_type", "is_current", "storage_policy"]
    search_fields = ["title", "description", "mime_type", "visit__pet__name", "pet__name"]


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "template_type", "is_active"]
    list_filter = ["template_type", "is_active"]
    search_fields = ["code", "name", "body_template"]


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "template", "visit", "owner", "pet", "lab_order", "generated_by", "generated_at"]
    list_filter = ["template", "generated_by"]
    search_fields = ["template__code", "template__name"]
