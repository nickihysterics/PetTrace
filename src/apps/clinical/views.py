from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import decorators, permissions, response, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import APIView

from apps.common.viewsets import RBACModelViewSet
from apps.users.access import ensure_user_can_access_branch_cabinet
from apps.visits.models import ProcedureOrder, Visit

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
from .serializers import (
    ClinicalAlertSerializer,
    ClinicalProtocolSerializer,
    ContraindicationRuleSerializer,
    DiagnosisCatalogSerializer,
    DoseCalcRequestSerializer,
    DoseCalcResponseSerializer,
    ProcedureChecklistItemSerializer,
    ProcedureChecklistSerializer,
    ProcedureChecklistTemplateItemSerializer,
    ProcedureChecklistTemplateSerializer,
    ProtocolMedicationTemplateSerializer,
    ProtocolProcedureTemplateSerializer,
    SymptomCatalogSerializer,
)
from .services import (
    apply_protocol_to_visit,
    calculate_recommended_dose_mg,
    complete_checklist_item,
    create_checklist_for_procedure,
)


class ClinicalProtocolViewSet(RBACModelViewSet):
    queryset = ClinicalProtocol.objects.prefetch_related("medication_templates", "procedure_templates").all()
    serializer_class = ClinicalProtocolSerializer
    filterset_fields = ["is_active", "species", "diagnosis_code"]
    search_fields = ["name", "diagnosis_code", "diagnosis_title"]
    action_permission_map = {"apply": ["apply_clinical_protocol"]}

    @decorators.action(detail=True, methods=["post"], url_path="apply")
    def apply(self, request, pk=None):
        protocol = self.get_object()
        visit_id = request.data.get("visit")
        if not visit_id:
            return response.Response({"detail": "visit is required"}, status=status.HTTP_400_BAD_REQUEST)

        visit = Visit.objects.filter(id=visit_id).first()
        if visit is None:
            return response.Response({"detail": "visit not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            ensure_user_can_access_branch_cabinet(
                user=request.user,
                branch=visit.branch,
                cabinet=visit.cabinet,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(detail)

        try:
            summary = apply_protocol_to_visit(
                protocol=protocol,
                visit=visit,
                actor=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return response.Response(summary)


class DiagnosisCatalogViewSet(RBACModelViewSet):
    queryset = DiagnosisCatalog.objects.all()
    serializer_class = DiagnosisCatalogSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "title", "description"]


class SymptomCatalogViewSet(RBACModelViewSet):
    queryset = SymptomCatalog.objects.all()
    serializer_class = SymptomCatalogSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "name", "description"]


class ProtocolMedicationTemplateViewSet(RBACModelViewSet):
    queryset = ProtocolMedicationTemplate.objects.select_related("protocol").all()
    serializer_class = ProtocolMedicationTemplateSerializer
    filterset_fields = ["protocol", "medication_name"]
    search_fields = ["medication_name", "protocol__name"]


class ProtocolProcedureTemplateViewSet(RBACModelViewSet):
    queryset = ProtocolProcedureTemplate.objects.select_related("protocol").all()
    serializer_class = ProtocolProcedureTemplateSerializer
    filterset_fields = ["protocol", "name"]
    search_fields = ["name", "protocol__name"]


class ContraindicationRuleViewSet(RBACModelViewSet):
    queryset = ContraindicationRule.objects.all()
    serializer_class = ContraindicationRuleSerializer
    filterset_fields = ["medication_name", "species", "severity", "is_active"]
    search_fields = ["medication_name", "allergy_keyword", "message"]


class ClinicalAlertViewSet(RBACModelViewSet):
    queryset = ClinicalAlert.objects.select_related("visit", "prescription", "rule", "resolved_by").all()
    serializer_class = ClinicalAlertSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit", "prescription", "severity", "rule", "resolved_by"]
    search_fields = ["message", "rule__medication_name", "visit__pet__name"]

    @decorators.action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if alert.resolved_at is not None:
            return response.Response(self.get_serializer(alert).data)

        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user if request.user.is_authenticated else None
        alert.save(update_fields=["resolved_at", "resolved_by", "updated_at"])
        return response.Response(self.get_serializer(alert).data)


class ProcedureChecklistTemplateViewSet(RBACModelViewSet):
    queryset = ProcedureChecklistTemplate.objects.prefetch_related("items").all()
    serializer_class = ProcedureChecklistTemplateSerializer
    filterset_fields = ["is_active", "procedure_name"]
    search_fields = ["name", "procedure_name"]


class ProcedureChecklistTemplateItemViewSet(RBACModelViewSet):
    queryset = ProcedureChecklistTemplateItem.objects.select_related("template").all()
    serializer_class = ProcedureChecklistTemplateItemSerializer
    filterset_fields = ["template", "is_required"]
    search_fields = ["title", "template__name"]


class ProcedureChecklistViewSet(RBACModelViewSet):
    queryset = ProcedureChecklist.objects.select_related("procedure_order", "template").prefetch_related("items").all()
    serializer_class = ProcedureChecklistSerializer
    scope_branch_field = "procedure_order__visit__branch"
    scope_cabinet_field = "procedure_order__visit__cabinet"
    filterset_fields = ["procedure_order", "template", "status"]

    @decorators.action(detail=False, methods=["post"], url_path="create-from-template")
    def create_from_template(self, request):
        procedure_order_id = request.data.get("procedure_order")
        template_id = request.data.get("template")
        if not procedure_order_id or not template_id:
            return response.Response(
                {"detail": "procedure_order and template are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        procedure_order = ProcedureOrder.objects.filter(id=procedure_order_id).first()
        if procedure_order is None:
            return response.Response({"detail": "procedure_order not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            ensure_user_can_access_branch_cabinet(
                user=request.user,
                branch=procedure_order.visit.branch,
                cabinet=procedure_order.visit.cabinet,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(detail)

        template = ProcedureChecklistTemplate.objects.filter(id=template_id).first()
        if template is None:
            return response.Response({"detail": "template not found"}, status=status.HTTP_404_NOT_FOUND)

        checklist = create_checklist_for_procedure(procedure_order=procedure_order, template=template)
        return response.Response(self.get_serializer(checklist).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], url_path="complete-item")
    def complete_item(self, request, pk=None):
        checklist = self.get_object()
        item_id = request.data.get("item")
        if not item_id:
            return response.Response({"detail": "item is required"}, status=status.HTTP_400_BAD_REQUEST)

        item = checklist.items.filter(id=item_id).first()
        if item is None:
            return response.Response({"detail": "item not found"}, status=status.HTTP_404_NOT_FOUND)

        completed_item = complete_checklist_item(
            checklist_item=item,
            actor=request.user if request.user.is_authenticated else None,
        )
        checklist.refresh_from_db()
        return response.Response(
            {
                "checklist": self.get_serializer(checklist).data,
                "item": ProcedureChecklistItemSerializer(completed_item).data,
            }
        )


class ProcedureChecklistItemViewSet(RBACModelViewSet):
    queryset = ProcedureChecklistItem.objects.select_related("checklist", "completed_by").all()
    serializer_class = ProcedureChecklistItemSerializer
    scope_branch_field = "checklist__procedure_order__visit__branch"
    scope_cabinet_field = "checklist__procedure_order__visit__cabinet"
    filterset_fields = ["checklist", "is_required", "is_completed", "completed_by"]
    search_fields = ["title"]


class DoseCalculatorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DoseCalcRequestSerializer,
        responses={
            200: DoseCalcResponseSerializer,
            404: OpenApiResponse(description="Шаблон медикамента не найден"),
        },
    )
    def post(self, request):
        weight_kg = Decimal(str(request.data.get("weight_kg", "0")))
        template_id = request.data.get("medication_template")
        if template_id is None:
            return response.Response(
                {"detail": "medication_template is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = ProtocolMedicationTemplate.objects.filter(id=template_id).first()
        if template is None:
            return response.Response({"detail": "medication_template not found"}, status=status.HTTP_404_NOT_FOUND)

        dose = calculate_recommended_dose_mg(
            weight_kg=weight_kg if weight_kg > 0 else None,
            medication_template=template,
        )
        return response.Response(
            {
                "medication_template": template.id,
                "medication_name": template.medication_name,
                "weight_kg": str(weight_kg),
                "recommended_dose_mg": str(dose),
            }
        )
