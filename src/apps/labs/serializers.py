from rest_framework import serializers

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


class LabOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabOrder
        fields = "__all__"
        read_only_fields = ["id", "public_id", "ordered_at", "completed_at", "created_at", "updated_at"]


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SpecimenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specimen
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class TubeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tube
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SpecimenTubeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecimenTube
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ContainerLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerLabel
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SpecimenEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecimenEvent
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SpecimenRecollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecimenRecollection
        fields = "__all__"
        read_only_fields = ["id", "public_id", "requested_at", "created_at", "updated_at"]


class LabParameterReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabParameterReference
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class LabResultValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResultValue
        fields = "__all__"
        read_only_fields = [
            "id",
            "public_id",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
