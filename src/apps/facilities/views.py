from django.db.models import Q

from apps.common.viewsets import RBACModelViewSet
from apps.users.access import get_role_default_cabinet_types, is_unrestricted_user

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
from .serializers import (
    BranchSerializer,
    CabinetSerializer,
    EquipmentSerializer,
    EquipmentTypeSerializer,
    HospitalBedSerializer,
    HospitalWardSerializer,
    OrganizationSerializer,
    ServiceRequirementEquipmentSerializer,
    ServiceRequirementSerializer,
    ServiceSerializer,
)


class OrganizationViewSet(RBACModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["name", "code", "created_at"]


class BranchViewSet(RBACModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    scope_branch_field = "id"
    scope_allow_unassigned = False
    filterset_fields = ["organization", "is_active"]
    search_fields = ["code", "name", "address"]
    ordering_fields = ["name", "code", "created_at"]


class CabinetViewSet(RBACModelViewSet):
    queryset = Cabinet.objects.select_related("branch").all()
    serializer_class = CabinetSerializer
    scope_branch_field = "branch"
    scope_cabinet_field = "id"
    scope_allow_unassigned = False
    filterset_fields = ["branch", "cabinet_type", "is_active"]
    search_fields = ["code", "name", "branch__code", "branch__name"]
    ordering_fields = ["branch__name", "code", "created_at"]


class EquipmentTypeViewSet(RBACModelViewSet):
    queryset = EquipmentType.objects.all()
    serializer_class = EquipmentTypeSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["name", "created_at"]


class EquipmentViewSet(RBACModelViewSet):
    queryset = Equipment.objects.select_related("branch", "cabinet", "equipment_type").all()
    serializer_class = EquipmentSerializer
    scope_branch_field = "branch"
    scope_cabinet_field = "cabinet"
    filterset_fields = ["branch", "cabinet", "equipment_type", "status", "is_active"]
    search_fields = ["code", "name", "branch__code", "equipment_type__code"]
    ordering_fields = ["branch__name", "name", "created_at"]


class ServiceRequirementViewSet(RBACModelViewSet):
    queryset = ServiceRequirement.objects.prefetch_related("required_equipment").all()
    serializer_class = ServiceRequirementSerializer
    filterset_fields = ["service", "service_type", "required_cabinet_type", "is_active"]
    search_fields = ["service_type", "description"]
    ordering_fields = ["service_type", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_unrestricted_user(self.request.user):
            return queryset

        role_cabinet_types = get_role_default_cabinet_types(self.request.user)
        if role_cabinet_types is None:
            return queryset
        return queryset.filter(
            Q(required_cabinet_type__in=role_cabinet_types) | Q(required_cabinet_type="")
        )


class ServiceViewSet(RBACModelViewSet):
    queryset = Service.objects.select_related("price_item").all()
    serializer_class = ServiceSerializer
    filterset_fields = ["category", "is_active", "price_item"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["name", "code", "created_at"]


class ServiceRequirementEquipmentViewSet(RBACModelViewSet):
    queryset = ServiceRequirementEquipment.objects.select_related("requirement", "equipment_type").all()
    serializer_class = ServiceRequirementEquipmentSerializer
    filterset_fields = ["requirement", "equipment_type"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_unrestricted_user(self.request.user):
            return queryset

        role_cabinet_types = get_role_default_cabinet_types(self.request.user)
        if role_cabinet_types is None:
            return queryset
        return queryset.filter(
            Q(requirement__required_cabinet_type__in=role_cabinet_types)
            | Q(requirement__required_cabinet_type="")
        )


class HospitalWardViewSet(RBACModelViewSet):
    queryset = HospitalWard.objects.select_related("branch").all()
    serializer_class = HospitalWardSerializer
    scope_branch_field = "branch"
    scope_allow_unassigned = False
    filterset_fields = ["branch", "is_active"]
    search_fields = ["code", "name", "branch__code", "branch__name"]
    ordering_fields = ["branch__name", "code", "created_at"]


class HospitalBedViewSet(RBACModelViewSet):
    queryset = HospitalBed.objects.select_related("ward", "ward__branch", "cabinet").all()
    serializer_class = HospitalBedSerializer
    scope_branch_field = "ward__branch"
    scope_cabinet_field = "cabinet"
    scope_allow_unassigned = False
    filterset_fields = ["ward", "cabinet", "status", "is_active", "is_isolation"]
    search_fields = ["code", "ward__code", "ward__name", "ward__branch__code"]
    ordering_fields = ["ward__branch__name", "ward__code", "code", "created_at"]
