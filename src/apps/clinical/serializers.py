from rest_framework import serializers

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


class ClinicalProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalProtocol
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class DiagnosisCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisCatalog
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SymptomCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomCatalog
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProtocolMedicationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtocolMedicationTemplate
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProtocolProcedureTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtocolProcedureTemplate
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ContraindicationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContraindicationRule
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ClinicalAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalAlert
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProcedureChecklistTemplateItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureChecklistTemplateItem
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProcedureChecklistTemplateSerializer(serializers.ModelSerializer):
    items = ProcedureChecklistTemplateItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProcedureChecklistTemplate
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class ProcedureChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureChecklistItem
        fields = "__all__"
        read_only_fields = ["id", "public_id", "completed_at", "created_at", "updated_at"]


class ProcedureChecklistSerializer(serializers.ModelSerializer):
    items = ProcedureChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProcedureChecklist
        fields = "__all__"
        read_only_fields = ["id", "public_id", "started_at", "completed_at", "created_at", "updated_at"]


class DoseCalcRequestSerializer(serializers.Serializer):
    medication_template = serializers.IntegerField()
    weight_kg = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default="0")


class DoseCalcResponseSerializer(serializers.Serializer):
    medication_template = serializers.IntegerField()
    medication_name = serializers.CharField()
    weight_kg = serializers.CharField()
    recommended_dose_mg = serializers.CharField()
