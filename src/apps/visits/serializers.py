from rest_framework import serializers

from .models import (
    Appointment,
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


class VisitSerializer(serializers.ModelSerializer):
    appointment_id = serializers.IntegerField(source="appointment.id", read_only=True)

    class Meta:
        model = Visit
        fields = [
            "id",
            "public_id",
            "pet",
            "owner",
            "veterinarian",
            "assistant",
            "status",
            "branch",
            "cabinet",
            "room",
            "scheduled_at",
            "started_at",
            "ended_at",
            "chief_complaint",
            "anamnesis",
            "physical_exam",
            "diagnosis_summary",
            "recommendations",
            "appointment_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "started_at", "ended_at", "appointment_id", "created_at", "updated_at"]
        extra_kwargs = {
            "owner": {"required": False},
        }

    def validate(self, attrs):
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        cabinet = attrs.get("cabinet", getattr(self.instance, "cabinet", None))
        if branch and cabinet and cabinet.branch_id != branch.id:
            raise serializers.ValidationError("cabinet does not belong to selected branch")
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = [
            "id",
            "public_id",
            "queue_number",
            "checked_in_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "owner": {"required": False},
            "end_at": {"required": False, "allow_null": True},
            "visit": {"required": False, "allow_null": True},
            "created_by": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        cabinet = attrs.get("cabinet", getattr(self.instance, "cabinet", None))
        if branch and cabinet and cabinet.branch_id != branch.id:
            raise serializers.ValidationError("cabinet does not belong to selected branch")
        return attrs


class VisitEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitEvent
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospitalization
        fields = "__all__"
        read_only_fields = ["id", "public_id", "admitted_at", "discharged_at", "created_at", "updated_at"]

    def validate(self, attrs):
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        cabinet = attrs.get("cabinet", getattr(self.instance, "cabinet", None))
        current_bed = attrs.get("current_bed", getattr(self.instance, "current_bed", None))
        if branch and cabinet and cabinet.branch_id != branch.id:
            raise serializers.ValidationError("cabinet does not belong to selected branch")
        if current_bed and current_bed.ward.branch_id != branch.id:
            raise serializers.ValidationError("current_bed does not belong to selected branch")
        return attrs


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        catalog_item = attrs.get("catalog_item", getattr(self.instance, "catalog_item", None))
        if catalog_item:
            if not attrs.get("code", getattr(self.instance, "code", "")):
                attrs["code"] = catalog_item.code
            if not attrs.get("title", getattr(self.instance, "title", "")):
                attrs["title"] = catalog_item.title
        return attrs


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        symptom = attrs.get("symptom", getattr(self.instance, "symptom", None))
        if symptom and not attrs.get("name", getattr(self.instance, "name", "")):
            attrs["name"] = symptom.name
        return attrs


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProcedureOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureOrder
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalBedStaySerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalBedStay
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalVitalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalVitalRecord
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class HospitalProcedurePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalProcedurePlan
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class MedicationAdministrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationAdministration
        fields = "__all__"
        read_only_fields = ["id", "public_id", "given_at", "given_by", "created_at", "updated_at"]
