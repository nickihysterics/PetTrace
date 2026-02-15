from rest_framework import serializers

from .models import ConsentDocument, Owner


class ConsentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentDocument
        fields = [
            "id",
            "public_id",
            "owner",
            "consent_type",
            "accepted_at",
            "document_file",
            "revoked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = [
            "id",
            "public_id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "notes",
            "discount_percent",
            "is_blacklisted",
            "preferred_branch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]
