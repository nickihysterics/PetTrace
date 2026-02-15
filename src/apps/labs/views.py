import csv
import io

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import decorators, response, status
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.viewsets import RBACModelViewSet, RBACReadOnlyModelViewSet
from apps.users.access import ensure_user_can_access_branch_cabinet

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
from .serializers import (
    ContainerLabelSerializer,
    LabOrderSerializer,
    LabParameterReferenceSerializer,
    LabResultValueSerializer,
    LabTestSerializer,
    SpecimenEventSerializer,
    SpecimenRecollectionSerializer,
    SpecimenSerializer,
    SpecimenTubeSerializer,
    TubeSerializer,
)
from .services import (
    apply_reference_and_flag,
    initialize_lab_order_workflow,
    maybe_notify_critical_result,
    process_collected_specimen_side_effects,
    sync_lab_order_status,
    transition_lab_order,
    transition_specimen,
)


class LabOrderViewSet(RBACModelViewSet):
    queryset = LabOrder.objects.select_related("visit", "ordered_by").all()
    serializer_class = LabOrderSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["status", "visit", "ordered_by"]
    search_fields = ["visit__pet__name", "visit__owner__phone", "notes"]
    ordering_fields = ["ordered_at", "completed_at", "created_at"]

    def perform_create(self, serializer):
        visit = serializer.validated_data.get("visit")
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        ordered_by = serializer.validated_data.get("ordered_by")
        if ordered_by is None and self.request.user.is_authenticated:
            ordered_by = self.request.user
        order = serializer.save(ordered_by=ordered_by)
        initialize_lab_order_workflow(order)

    def perform_update(self, serializer):
        visit = serializer.validated_data.get("visit", serializer.instance.visit)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="transition")
    @transaction.atomic
    def transition(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return response.Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transition_lab_order(
                order=order,
                new_status=new_status,
                actor=request.user if request.user.is_authenticated else None,
                location=request.data.get("location", ""),
                notes=request.data.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(order)
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], url_path="import-results-csv")
    @transaction.atomic
    def import_results_csv(self, request, pk=None):
        order = self.get_object()
        file_obj = request.FILES.get("file")
        if file_obj is None:
            return response.Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file_obj.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return response.Response({"detail": "file must be UTF-8 encoded CSV"}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(decoded))
        if reader.fieldnames is None:
            return response.Response({"detail": "CSV header is missing"}, status=status.HTTP_400_BAD_REQUEST)

        required_columns = {"test_code", "parameter_name", "value"}
        missing_columns = sorted(required_columns - set(reader.fieldnames))
        if missing_columns:
            return response.Response(
                {"detail": f"missing CSV columns: {', '.join(missing_columns)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_results = 0
        updated_results = 0
        tests_touched: set[int] = set()

        for row in reader:
            test_code = (row.get("test_code") or "").strip()
            parameter_name = (row.get("parameter_name") or "").strip()
            value = (row.get("value") or "").strip()
            if not test_code or not parameter_name:
                continue

            lab_test = order.tests.filter(code=test_code).first()
            if lab_test is None:
                lab_test = LabTest.objects.create(
                    lab_order=order,
                    code=test_code,
                    name=(row.get("test_name") or test_code)[:255],
                    specimen_type=(row.get("specimen_type") or "OTHER")[:64],
                    status=LabTest.LabTestStatus.IN_PROCESS,
                )

            result, created = LabResultValue.objects.update_or_create(
                lab_test=lab_test,
                parameter_name=parameter_name,
                defaults={
                    "value": value,
                    "unit": (row.get("unit") or "")[:32],
                    "reference_range": (row.get("reference_range") or "")[:120],
                    "flag": (row.get("flag") or LabResultValue.Flag.NORMAL)[:16],
                    "comment": row.get("comment") or "",
                    "source": "CSV_IMPORT",
                },
            )
            apply_reference_and_flag(result)
            tests_touched.add(lab_test.id)
            if created:
                created_results += 1
            else:
                updated_results += 1

        if tests_touched:
            LabTest.objects.filter(id__in=tests_touched).update(
                status=LabTest.LabTestStatus.DONE,
                updated_at=timezone.now(),
            )
        sync_lab_order_status(order)
        return response.Response(
            {
                "lab_order": order.id,
                "created_results": created_results,
                "updated_results": updated_results,
                "tests_touched": len(tests_touched),
            }
        )


class LabTestViewSet(RBACModelViewSet):
    queryset = LabTest.objects.select_related("lab_order").all()
    serializer_class = LabTestSerializer
    scope_branch_field = "lab_order__visit__branch"
    scope_cabinet_field = "lab_order__visit__cabinet"
    filterset_fields = ["lab_order", "status", "specimen_type"]
    search_fields = ["code", "name"]

    def perform_create(self, serializer):
        lab_order = serializer.validated_data.get("lab_order")
        visit = getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        lab_order = serializer.validated_data.get("lab_order", serializer.instance.lab_order)
        visit = getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()


class SpecimenViewSet(RBACModelViewSet):
    queryset = Specimen.objects.select_related("lab_order", "collected_by").all()
    serializer_class = SpecimenSerializer
    scope_branch_field = "lab_order__visit__branch"
    scope_cabinet_field = "lab_order__visit__cabinet"
    filterset_fields = ["lab_order", "status", "specimen_type"]
    search_fields = ["lab_order__visit__pet__name", "lab_order__visit__owner__phone"]

    def perform_create(self, serializer):
        lab_order = serializer.validated_data.get("lab_order")
        visit = getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        lab_order = serializer.validated_data.get("lab_order", serializer.instance.lab_order)
        visit = getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="transition")
    @transaction.atomic
    def transition(self, request, pk=None):
        specimen = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return response.Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transition_specimen(
                specimen=specimen,
                new_status=new_status,
                actor=request.user if request.user.is_authenticated else None,
                location=request.data.get("location", ""),
                notes=request.data.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        return response.Response(self.get_serializer(specimen).data)

    @decorators.action(detail=True, methods=["post"], url_path="mark-collected")
    @transaction.atomic
    def mark_collected(self, request, pk=None):
        specimen = self.get_object()
        try:
            transition_specimen(
                specimen=specimen,
                new_status=Specimen.SpecimenStatus.COLLECTED,
                actor=request.user if request.user.is_authenticated else None,
                location=request.data.get("collection_room", ""),
                notes=request.data.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        return response.Response(self.get_serializer(specimen).data)

    @decorators.action(detail=True, methods=["post"], url_path="request-recollection")
    @transaction.atomic
    def request_recollection(self, request, pk=None):
        specimen = self.get_object()
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return response.Response({"detail": "reason is required"}, status=status.HTTP_400_BAD_REQUEST)

        if specimen.status not in {
            Specimen.SpecimenStatus.REJECTED,
            Specimen.SpecimenStatus.COLLECTED,
            Specimen.SpecimenStatus.RECEIVED,
        }:
            return response.Response(
                {"detail": f"cannot request recollection from status {specimen.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_specimen = Specimen.objects.create(
            lab_order=specimen.lab_order,
            specimen_type=specimen.specimen_type,
            status=Specimen.SpecimenStatus.PLANNED,
            collection_room=specimen.collection_room,
        )
        recollection = SpecimenRecollection.objects.create(
            original_specimen=specimen,
            recollected_specimen=new_specimen,
            reason=reason,
            status=SpecimenRecollection.RecollectionStatus.CREATED,
            requested_by=request.user if request.user.is_authenticated else None,
            note=request.data.get("note", ""),
        )

        sync_lab_order_status(specimen.lab_order)
        return response.Response(
            {
                "recollection": SpecimenRecollectionSerializer(recollection).data,
                "new_specimen": SpecimenSerializer(new_specimen).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TubeViewSet(RBACModelViewSet):
    queryset = Tube.objects.select_related("inventory_item").all()
    serializer_class = TubeSerializer
    filterset_fields = ["tube_type", "inventory_item"]
    search_fields = ["code", "lot_number"]


class SpecimenTubeViewSet(RBACModelViewSet):
    queryset = SpecimenTube.objects.select_related("specimen", "tube", "tube__inventory_item").all()
    serializer_class = SpecimenTubeSerializer
    scope_branch_field = "specimen__lab_order__visit__branch"
    scope_cabinet_field = "specimen__lab_order__visit__cabinet"
    filterset_fields = ["specimen", "tube"]

    def perform_create(self, serializer):
        specimen = serializer.validated_data.get("specimen")
        visit = getattr(getattr(specimen, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        specimen_tube = serializer.save()
        if specimen_tube.specimen.status == Specimen.SpecimenStatus.COLLECTED:
            process_collected_specimen_side_effects(
                specimen_tube.specimen,
                actor=self.request.user if self.request.user.is_authenticated else None,
            )

    def perform_update(self, serializer):
        specimen = serializer.validated_data.get("specimen", serializer.instance.specimen)
        visit = getattr(getattr(specimen, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()


class ContainerLabelViewSet(RBACModelViewSet):
    queryset = ContainerLabel.objects.select_related("specimen").all()
    serializer_class = ContainerLabelSerializer
    scope_branch_field = "specimen__lab_order__visit__branch"
    scope_cabinet_field = "specimen__lab_order__visit__cabinet"
    filterset_fields = ["specimen"]
    search_fields = ["label_value"]

    def perform_create(self, serializer):
        specimen = serializer.validated_data.get("specimen")
        visit = getattr(getattr(specimen, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        specimen = serializer.validated_data.get("specimen", serializer.instance.specimen)
        visit = getattr(getattr(specimen, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()


class SpecimenEventViewSet(RBACReadOnlyModelViewSet):
    queryset = SpecimenEvent.objects.select_related("specimen", "actor").all()
    serializer_class = SpecimenEventSerializer
    scope_branch_field = "specimen__lab_order__visit__branch"
    scope_cabinet_field = "specimen__lab_order__visit__cabinet"
    filterset_fields = ["specimen", "to_status", "actor"]


class SpecimenRecollectionViewSet(RBACModelViewSet):
    queryset = SpecimenRecollection.objects.select_related(
        "original_specimen",
        "recollected_specimen",
        "requested_by",
    ).all()
    serializer_class = SpecimenRecollectionSerializer
    scope_branch_field = "original_specimen__lab_order__visit__branch"
    scope_cabinet_field = "original_specimen__lab_order__visit__cabinet"
    filterset_fields = ["original_specimen", "recollected_specimen", "status", "requested_by"]
    search_fields = ["reason", "note"]


class LabParameterReferenceViewSet(RBACModelViewSet):
    queryset = LabParameterReference.objects.all()
    serializer_class = LabParameterReferenceSerializer
    filterset_fields = ["parameter_name", "species", "unit", "is_active"]
    search_fields = ["parameter_name", "note", "unit"]


class LabResultValueViewSet(RBACModelViewSet):
    queryset = LabResultValue.objects.select_related("lab_test", "lab_test__lab_order", "approved_by").all()
    serializer_class = LabResultValueSerializer
    scope_branch_field = "lab_test__lab_order__visit__branch"
    scope_cabinet_field = "lab_test__lab_order__visit__cabinet"
    filterset_fields = ["lab_test", "flag", "approved_by"]
    search_fields = ["parameter_name", "value"]
    action_permission_map = {
        "approve": ["approve_lab_result"],
    }

    def perform_create(self, serializer):
        lab_test = serializer.validated_data.get("lab_test")
        visit = getattr(getattr(lab_test, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        result = serializer.save()
        apply_reference_and_flag(result)
        maybe_notify_critical_result(result)
        sync_lab_order_status(result.lab_test.lab_order)

    def perform_update(self, serializer):
        lab_test = serializer.validated_data.get("lab_test", serializer.instance.lab_test)
        visit = getattr(getattr(lab_test, "lab_order", None), "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        result = serializer.save()
        apply_reference_and_flag(result)
        maybe_notify_critical_result(result)
        sync_lab_order_status(result.lab_test.lab_order)

    @decorators.action(detail=True, methods=["post"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None):
        result = self.get_object()
        if result.approved_at is not None:
            return response.Response({"detail": "result already approved"}, status=status.HTTP_400_BAD_REQUEST)

        result.approved_by = request.user
        result.approved_at = timezone.now()
        result.approval_note = request.data.get("note", "")
        result.save(update_fields=["approved_by", "approved_at", "approval_note", "updated_at"])

        if result.lab_test.status != LabTest.LabTestStatus.DONE:
            result.lab_test.status = LabTest.LabTestStatus.DONE
            result.lab_test.save(update_fields=["status", "updated_at"])

        return response.Response(self.get_serializer(result).data)
