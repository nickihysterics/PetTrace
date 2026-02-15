from rest_framework import serializers

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


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class CabinetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cabinet
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class EquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ServiceRequirementEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequirementEquipment
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ServiceRequirementSerializer(serializers.ModelSerializer):
    required_equipment = ServiceRequirementEquipmentSerializer(many=True, read_only=True)
    display_service_type = serializers.CharField(read_only=True)

    class Meta:
        model = ServiceRequirement
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        service = attrs.get("service", getattr(self.instance, "service", None))
        service_type = attrs.get("service_type", getattr(self.instance, "service_type", ""))
        if not service and not service_type:
            raise serializers.ValidationError("service or service_type is required")
        return attrs


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalWardSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalWard
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalBedSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalBed
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]
