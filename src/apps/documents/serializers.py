from rest_framework import serializers

from .models import ClinicalDocument, DocumentStoragePolicy, DocumentTemplate, GeneratedDocument


class DocumentStoragePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentStoragePolicy
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ClinicalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalDocument
        fields = "__all__"
        read_only_fields = [
            "id",
            "public_id",
            "document_uid",
            "version",
            "is_current",
            "previous_version",
            "uploaded_by",
            "replaced_at",
            "replaced_by",
            "created_at",
            "updated_at",
        ]


class DocumentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDocument
        fields = "__all__"
        read_only_fields = ["id", "public_id", "generated_by", "generated_at", "created_at", "updated_at"]
