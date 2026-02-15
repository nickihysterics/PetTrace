from rest_framework import serializers

from .models import Pet, PetAttachment


class PetAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetAttachment
        fields = [
            "id",
            "public_id",
            "pet",
            "file",
            "title",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class PetSerializer(serializers.ModelSerializer):
    qr_value = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = [
            "id",
            "public_id",
            "owner",
            "name",
            "species",
            "breed",
            "sex",
            "birth_date",
            "weight_kg",
            "allergies",
            "vaccination_notes",
            "insurance_number",
            "microchip_id",
            "qr_token",
            "qr_value",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "qr_token", "qr_value", "created_at", "updated_at"]

    def get_qr_value(self, obj) -> str:
        return f"pet:{obj.qr_token}"
