from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import decorators, response, status
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.viewsets import RBACModelViewSet, RBACReadOnlyModelViewSet
from apps.facilities.services import get_service_requirement, validate_appointment_resources
from apps.inventory.services import write_off_inventory_item
from apps.users.access import ensure_user_can_access_branch_cabinet

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
from .queue import allocate_appointment_queue_number
from .serializers import (
    AppointmentSerializer,
    DiagnosisSerializer,
    HospitalBedStaySerializer,
    HospitalizationSerializer,
    HospitalProcedurePlanSerializer,
    HospitalVitalRecordSerializer,
    MedicationAdministrationSerializer,
    ObservationSerializer,
    PrescriptionSerializer,
    ProcedureOrderSerializer,
    VisitEventSerializer,
    VisitSerializer,
)


def _create_visit_event(visit: Visit, from_status: str, to_status: str, actor=None, notes: str = "") -> VisitEvent:
    return VisitEvent.objects.create(
        visit=visit,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        notes=notes,
    )


def _close_current_bed_stay(hospitalization: Hospitalization, actor=None, notes: str = "") -> None:
    current_stay = hospitalization.bed_stays.filter(is_current=True).order_by("-moved_in_at").first()
    if current_stay is None:
        return

    current_stay.is_current = False
    current_stay.moved_out_at = timezone.now()
    if notes:
        current_stay.notes = notes
    if actor and current_stay.moved_by_id is None:
        current_stay.moved_by = actor
    current_stay.save(update_fields=["is_current", "moved_out_at", "notes", "moved_by", "updated_at"])


def _assign_hospitalization_bed(
    hospitalization: Hospitalization,
    bed,
    *,
    actor=None,
    notes: str = "",
) -> Hospitalization:
    if bed is None:
        raise ValidationError("bed is required")
    if bed.ward.branch_id != hospitalization.branch_id:
        raise ValidationError("bed does not belong to hospitalization branch")
    if not bed.is_active:
        raise ValidationError("selected bed is inactive")
    if bed.status not in {
        bed.BedStatus.AVAILABLE,
        bed.BedStatus.OCCUPIED,
    }:
        raise ValidationError(f"selected bed is not assignable in status {bed.status}")
    if bed.status == bed.BedStatus.OCCUPIED and not Hospitalization.objects.filter(
        id=hospitalization.id,
        current_bed=bed,
    ).exists():
        raise ValidationError("selected bed is already occupied")

    previous_bed = hospitalization.current_bed
    if previous_bed and previous_bed.id == bed.id:
        return hospitalization

    if previous_bed and previous_bed.status == previous_bed.BedStatus.OCCUPIED:
        previous_bed.status = previous_bed.BedStatus.AVAILABLE
        previous_bed.save(update_fields=["status", "updated_at"])
        _close_current_bed_stay(
            hospitalization,
            actor=actor,
            notes=f"Moved from bed {previous_bed.code}: {notes}".strip(),
        )

    bed.status = bed.BedStatus.OCCUPIED
    bed.save(update_fields=["status", "updated_at"])

    hospitalization.current_bed = bed
    if hospitalization.cabinet is None and bed.cabinet_id:
        hospitalization.cabinet = bed.cabinet
    hospitalization.save(update_fields=["current_bed", "cabinet", "updated_at"])

    HospitalBedStay.objects.create(
        hospitalization=hospitalization,
        bed=bed,
        moved_by=actor,
        notes=notes,
    )
    return hospitalization


class VisitViewSet(RBACModelViewSet):
    queryset = Visit.objects.select_related("pet", "owner", "veterinarian", "assistant", "branch", "cabinet").all()
    serializer_class = VisitSerializer
    scope_branch_field = "branch"
    scope_cabinet_field = "cabinet"
    filterset_fields = ["status", "pet", "owner", "veterinarian", "branch", "cabinet"]
    search_fields = ["pet__name", "owner__phone", "owner__last_name", "room"]
    ordering_fields = ["created_at", "scheduled_at", "started_at"]

    def perform_create(self, serializer):
        pet = serializer.validated_data.get("pet")
        owner = serializer.validated_data.get("owner")
        branch = serializer.validated_data.get("branch")
        cabinet = serializer.validated_data.get("cabinet")
        room = serializer.validated_data.get("room", "")
        if owner is None and pet is not None:
            owner = pet.owner
        if branch is None and cabinet is not None:
            branch = cabinet.branch
        if branch and cabinet and cabinet.branch_id != branch.id:
            raise DRFValidationError("cabinet does not belong to selected branch")
        if not room and cabinet is not None:
            room = cabinet.code
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=branch,
                cabinet=cabinet,
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        visit = serializer.save(owner=owner, branch=branch, room=room)
        _create_visit_event(
            visit=visit,
            from_status="",
            to_status=visit.status,
            actor=self.request.user if self.request.user.is_authenticated else None,
            notes="Visit created",
        )

    def perform_update(self, serializer):
        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        cabinet = serializer.validated_data.get("cabinet", serializer.instance.cabinet)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=branch,
                cabinet=cabinet,
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="transition")
    @transaction.atomic
    def transition(self, request, pk=None):
        visit = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return response.Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == Visit.VisitStatus.CLOSED and not request.user.has_perm("visits.close_visit"):
            return response.Response(
                {"detail": "permission denied: visits.close_visit is required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        previous = visit.status
        try:
            visit.transition_to(new_status)
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        visit.save(update_fields=["status", "started_at", "ended_at", "updated_at"])
        _create_visit_event(
            visit=visit,
            from_status=previous,
            to_status=visit.status,
            actor=request.user if request.user.is_authenticated else None,
            notes=request.data.get("notes", ""),
        )

        serializer = self.get_serializer(visit)
        return response.Response(serializer.data)


class AppointmentViewSet(RBACModelViewSet):
    queryset = Appointment.objects.select_related(
        "owner",
        "pet",
        "veterinarian",
        "visit",
        "created_by",
        "branch",
        "cabinet",
    ).all()
    serializer_class = AppointmentSerializer
    scope_branch_field = "branch"
    scope_cabinet_field = "cabinet"
    filterset_fields = ["status", "owner", "pet", "veterinarian", "room", "branch", "cabinet"]
    search_fields = ["owner__phone", "owner__last_name", "pet__name", "service_type", "notes"]
    ordering_fields = ["start_at", "created_at", "queue_number"]

    def _prepare_appointment_fields(self, serializer):
        instance = getattr(serializer, "instance", None)
        pet = serializer.validated_data.get("pet", getattr(instance, "pet", None))
        owner = serializer.validated_data.get("owner", getattr(instance, "owner", None))
        branch = serializer.validated_data.get("branch", getattr(instance, "branch", None))
        cabinet = serializer.validated_data.get("cabinet", getattr(instance, "cabinet", None))
        start_at = serializer.validated_data.get("start_at", getattr(instance, "start_at", None))
        duration = serializer.validated_data.get("duration_minutes", getattr(instance, "duration_minutes", 30))
        end_at = serializer.validated_data.get("end_at", getattr(instance, "end_at", None))
        service = serializer.validated_data.get("service", getattr(instance, "service", None))
        service_type = serializer.validated_data.get("service_type", getattr(instance, "service_type", ""))
        room = serializer.validated_data.get("room", getattr(instance, "room", ""))

        if owner is None and pet is not None:
            owner = pet.owner
        if branch is None and cabinet is not None:
            branch = cabinet.branch

        if service and not service_type:
            service_type = service.code

        requirement = get_service_requirement(service_type, service=service)
        if "duration_minutes" not in self.request.data and requirement is not None:
            duration = requirement.default_duration_minutes
        if "duration_minutes" not in self.request.data and requirement is None and service is not None:
            duration = service.default_duration_minutes
        if "end_at" not in self.request.data and start_at is not None:
            end_at = start_at + timedelta(minutes=duration)
        if not room and cabinet is not None:
            room = cabinet.code

        return {
            "owner": owner,
            "branch": branch,
            "cabinet": cabinet,
            "start_at": start_at,
            "end_at": end_at,
            "duration_minutes": duration,
            "service": service,
            "service_type": service_type,
            "room": room,
        }

    def perform_create(self, serializer):
        prepared = self._prepare_appointment_fields(serializer)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=prepared["branch"],
                cabinet=prepared["cabinet"],
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        try:
            validate_appointment_resources(
                appointment_model=Appointment,
                branch=prepared["branch"],
                cabinet=prepared["cabinet"],
                service_type=prepared["service_type"],
                service=prepared["service"],
                start_at=prepared["start_at"],
                end_at=prepared["end_at"],
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        serializer.save(
            owner=prepared["owner"],
            branch=prepared["branch"],
            end_at=prepared["end_at"],
            duration_minutes=prepared["duration_minutes"],
            service=prepared["service"],
            service_type=prepared["service_type"],
            room=prepared["room"],
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )

    def perform_update(self, serializer):
        appointment = self.get_object()
        prepared = self._prepare_appointment_fields(serializer)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=prepared["branch"],
                cabinet=prepared["cabinet"],
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        try:
            validate_appointment_resources(
                appointment_model=Appointment,
                branch=prepared["branch"],
                cabinet=prepared["cabinet"],
                service_type=prepared["service_type"],
                service=prepared["service"],
                start_at=prepared["start_at"],
                end_at=prepared["end_at"],
                ignore_appointment_id=appointment.id,
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        serializer.save(
            owner=prepared["owner"],
            branch=prepared["branch"],
            end_at=prepared["end_at"],
            duration_minutes=prepared["duration_minutes"],
            service=prepared["service"],
            service_type=prepared["service_type"],
            room=prepared["room"],
        )

    @decorators.action(detail=True, methods=["post"], url_path="transition")
    @transaction.atomic
    def transition(self, request, pk=None):
        appointment = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return response.Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            appointment.transition_to(new_status)
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        appointment.save(update_fields=["status", "checked_in_at", "completed_at", "updated_at"])
        return response.Response(self.get_serializer(appointment).data)

    @decorators.action(detail=True, methods=["post"], url_path="check-in")
    @transaction.atomic
    def check_in(self, request, pk=None):
        if not self.get_queryset().filter(pk=pk).exists():
            return response.Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        appointment = Appointment.objects.select_for_update().filter(pk=pk).first()
        if appointment is None:
            return response.Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status not in {
            Appointment.AppointmentStatus.BOOKED,
            Appointment.AppointmentStatus.CHECKED_IN,
        }:
            return response.Response(
                {"detail": f"cannot check in appointment in status {appointment.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.status == Appointment.AppointmentStatus.BOOKED:
            try:
                appointment.transition_to(Appointment.AppointmentStatus.CHECKED_IN)
            except ValidationError as exc:
                detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
                return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        if appointment.queue_number is None:
            appointment.queue_number = allocate_appointment_queue_number(
                appointment=appointment
            )

        appointment.save(update_fields=["status", "checked_in_at", "queue_number", "updated_at"])
        return response.Response(self.get_serializer(appointment).data)

    @decorators.action(detail=True, methods=["post"], url_path="start-visit")
    @transaction.atomic
    def start_visit(self, request, pk=None):
        if not self.get_queryset().filter(pk=pk).exists():
            return response.Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        appointment = Appointment.objects.select_for_update().filter(pk=pk).first()
        if appointment is None:
            return response.Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if appointment.visit_id is not None:
            visit = appointment.visit
            return response.Response(
                {
                    "appointment": self.get_serializer(appointment).data,
                    "visit": VisitSerializer(visit).data,
                }
            )

        if not request.user.has_perm("visits.add_visit"):
            return response.Response(
                {"detail": "permission denied: visits.add_visit is required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status in {
            Appointment.AppointmentStatus.CANCELED,
            Appointment.AppointmentStatus.NO_SHOW,
            Appointment.AppointmentStatus.COMPLETED,
        }:
            return response.Response(
                {"detail": f"cannot start visit from appointment status {appointment.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.status == Appointment.AppointmentStatus.BOOKED:
            appointment.transition_to(Appointment.AppointmentStatus.CHECKED_IN)

        if appointment.status == Appointment.AppointmentStatus.CHECKED_IN:
            appointment.transition_to(Appointment.AppointmentStatus.IN_ROOM)

        visit = Visit.objects.create(
            pet=appointment.pet,
            owner=appointment.owner,
            veterinarian=appointment.veterinarian,
            status=Visit.VisitStatus.WAITING,
            branch=appointment.branch,
            cabinet=appointment.cabinet,
            room=appointment.room,
            scheduled_at=appointment.start_at,
            chief_complaint=request.data.get("chief_complaint", ""),
        )

        prev_visit_status = visit.status
        visit.transition_to(Visit.VisitStatus.IN_PROGRESS)
        visit.save(update_fields=["status", "started_at", "updated_at"])
        _create_visit_event(
            visit=visit,
            from_status=prev_visit_status,
            to_status=visit.status,
            actor=request.user if request.user.is_authenticated else None,
            notes="Visit started from appointment",
        )

        appointment.visit = visit
        appointment.save(update_fields=["status", "checked_in_at", "visit", "updated_at"])

        return response.Response(
            {
                "appointment": self.get_serializer(appointment).data,
                "visit": VisitSerializer(visit).data,
            }
        )

    @decorators.action(detail=True, methods=["post"], url_path="complete")
    @transaction.atomic
    def complete(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status != Appointment.AppointmentStatus.IN_ROOM:
            return response.Response(
                {"detail": "appointment must be IN_ROOM to complete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.visit and appointment.visit.status == Visit.VisitStatus.IN_PROGRESS:
            if not request.user.has_perm("visits.change_visit"):
                return response.Response(
                    {"detail": "permission denied: visits.change_visit is required"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        appointment.transition_to(Appointment.AppointmentStatus.COMPLETED)
        appointment.save(update_fields=["status", "completed_at", "updated_at"])

        if appointment.visit and appointment.visit.status == Visit.VisitStatus.IN_PROGRESS:
            previous = appointment.visit.status
            appointment.visit.transition_to(Visit.VisitStatus.COMPLETED)
            appointment.visit.save(update_fields=["status", "ended_at", "updated_at"])
            _create_visit_event(
                visit=appointment.visit,
                from_status=previous,
                to_status=appointment.visit.status,
                actor=request.user if request.user.is_authenticated else None,
                notes="Visit auto-completed from appointment",
            )

        return response.Response(self.get_serializer(appointment).data)


class VisitEventViewSet(RBACReadOnlyModelViewSet):
    queryset = VisitEvent.objects.select_related("visit", "actor").all()
    serializer_class = VisitEventSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit", "to_status", "actor"]
    search_fields = ["visit__id", "notes", "actor__email"]


class HospitalizationViewSet(RBACModelViewSet):
    queryset = Hospitalization.objects.select_related("visit", "branch", "cabinet").all()
    serializer_class = HospitalizationSerializer
    scope_branch_field = "branch"
    scope_cabinet_field = "cabinet"
    filterset_fields = ["visit", "branch", "cabinet", "status"]
    search_fields = ["visit__pet__name", "visit__owner__phone", "cage_number", "care_plan"]

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        cabinet = serializer.validated_data.get("cabinet")
        bed = serializer.validated_data.get("current_bed")
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=branch,
                cabinet=cabinet,
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        if bed is not None:
            hospitalization = serializer.save(current_bed=None)
        else:
            hospitalization = serializer.save()
        if bed is not None:
            try:
                _assign_hospitalization_bed(
                    hospitalization,
                    bed,
                    actor=self.request.user if self.request.user.is_authenticated else None,
                    notes="Initial bed assignment",
                )
            except ValidationError as exc:
                raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

    def perform_update(self, serializer):
        previous_bed_id = serializer.instance.current_bed_id
        previous_bed_obj = serializer.instance.current_bed
        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        cabinet = serializer.validated_data.get("cabinet", serializer.instance.cabinet)
        bed = serializer.validated_data.get("current_bed", serializer.instance.current_bed)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=branch,
                cabinet=cabinet,
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        if bed is not None:
            hospitalization = serializer.save(current_bed=serializer.instance.current_bed)
        else:
            hospitalization = serializer.save()
        if bed is not None and previous_bed_id != bed.id:
            try:
                _assign_hospitalization_bed(
                    hospitalization,
                    bed,
                    actor=self.request.user if self.request.user.is_authenticated else None,
                    notes="Bed updated via API",
                )
            except ValidationError as exc:
                raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        elif bed is None and previous_bed_id:
            _close_current_bed_stay(
                hospitalization,
                actor=self.request.user if self.request.user.is_authenticated else None,
                notes="Bed assignment removed",
            )
            if previous_bed_obj and previous_bed_obj.status == previous_bed_obj.BedStatus.OCCUPIED:
                previous_bed_obj.status = previous_bed_obj.BedStatus.AVAILABLE
                previous_bed_obj.save(update_fields=["status", "updated_at"])

    @decorators.action(detail=True, methods=["post"], url_path="transition")
    @transaction.atomic
    def transition(self, request, pk=None):
        hospitalization = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return response.Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            hospitalization.transition_to(new_status)
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        if new_status in {
            Hospitalization.HospitalizationStatus.DISCHARGED,
            Hospitalization.HospitalizationStatus.CANCELED,
        } and hospitalization.current_bed_id:
            bed = hospitalization.current_bed
            _close_current_bed_stay(
                hospitalization,
                actor=request.user if request.user.is_authenticated else None,
                notes=f"Hospitalization finished with status {new_status}",
            )
            if bed and bed.status == bed.BedStatus.OCCUPIED:
                bed.status = bed.BedStatus.CLEANING
                bed.save(update_fields=["status", "updated_at"])
            hospitalization.current_bed = None

        hospitalization.save(update_fields=["status", "discharged_at", "current_bed", "updated_at"])
        return response.Response(self.get_serializer(hospitalization).data)

    @decorators.action(detail=True, methods=["post"], url_path="assign-bed")
    @transaction.atomic
    def assign_bed(self, request, pk=None):
        from apps.facilities.models import HospitalBed

        hospitalization = self.get_object()
        bed_id = request.data.get("bed")
        if not bed_id:
            return response.Response({"detail": "bed is required"}, status=status.HTTP_400_BAD_REQUEST)
        bed_obj = HospitalBed.objects.select_related("ward", "cabinet").filter(
            id=bed_id,
            ward__branch=hospitalization.branch,
        ).first()
        if bed_obj is None:
            return response.Response(
                {"detail": "bed does not belong to hospitalization branch"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            _assign_hospitalization_bed(
                hospitalization,
                bed_obj,
                actor=request.user if request.user.is_authenticated else None,
                notes=request.data.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        return response.Response(self.get_serializer(hospitalization).data)


class DiagnosisViewSet(RBACModelViewSet):
    queryset = Diagnosis.objects.select_related("visit").all()
    serializer_class = DiagnosisSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit", "is_primary"]
    search_fields = ["title", "code"]

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
        serializer.save()

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


class ObservationViewSet(RBACModelViewSet):
    queryset = Observation.objects.select_related("visit").all()
    serializer_class = ObservationSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit", "name"]
    search_fields = ["name", "value"]

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
        serializer.save()

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


class PrescriptionViewSet(RBACModelViewSet):
    queryset = Prescription.objects.select_related("visit").all()
    serializer_class = PrescriptionSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit"]
    search_fields = ["medication_name", "warnings"]

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
        serializer.save()

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


class ProcedureOrderViewSet(RBACModelViewSet):
    queryset = ProcedureOrder.objects.select_related("visit", "performed_by").all()
    serializer_class = ProcedureOrderSerializer
    scope_branch_field = "visit__branch"
    scope_cabinet_field = "visit__cabinet"
    filterset_fields = ["visit", "status", "performed_by"]
    search_fields = ["name", "instructions"]

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
        serializer.save()


class HospitalBedStayViewSet(RBACReadOnlyModelViewSet):
    queryset = HospitalBedStay.objects.select_related("hospitalization", "bed", "bed__ward", "moved_by").all()
    serializer_class = HospitalBedStaySerializer
    scope_branch_field = "hospitalization__branch"
    scope_cabinet_field = "bed__cabinet"
    filterset_fields = ["hospitalization", "bed", "is_current"]
    search_fields = ["hospitalization__visit__pet__name", "bed__code", "notes"]


class HospitalVitalRecordViewSet(RBACModelViewSet):
    queryset = HospitalVitalRecord.objects.select_related("hospitalization", "recorded_by").all()
    serializer_class = HospitalVitalRecordSerializer
    scope_branch_field = "hospitalization__branch"
    scope_cabinet_field = "hospitalization__cabinet"
    filterset_fields = ["hospitalization", "recorded_by", "appetite_status"]
    search_fields = ["hospitalization__visit__pet__name", "notes"]

    def perform_create(self, serializer):
        hospitalization = serializer.validated_data.get("hospitalization")
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(hospitalization, "branch", None),
                cabinet=getattr(hospitalization, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save(recorded_by=self.request.user if self.request.user.is_authenticated else None)

    def perform_update(self, serializer):
        hospitalization = serializer.validated_data.get("hospitalization", serializer.instance.hospitalization)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(hospitalization, "branch", None),
                cabinet=getattr(hospitalization, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()


class HospitalProcedurePlanViewSet(RBACModelViewSet):
    queryset = HospitalProcedurePlan.objects.select_related("hospitalization", "completed_by").all()
    serializer_class = HospitalProcedurePlanSerializer
    scope_branch_field = "hospitalization__branch"
    scope_cabinet_field = "hospitalization__cabinet"
    filterset_fields = ["hospitalization", "status", "completed_by"]
    search_fields = ["title", "instructions", "notes"]

    def perform_create(self, serializer):
        hospitalization = serializer.validated_data.get("hospitalization")
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(hospitalization, "branch", None),
                cabinet=getattr(hospitalization, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        hospitalization = serializer.validated_data.get("hospitalization", serializer.instance.hospitalization)
        status_value = serializer.validated_data.get("status", serializer.instance.status)
        completed_by = serializer.validated_data.get("completed_by", serializer.instance.completed_by)
        completed_at = serializer.validated_data.get("completed_at", serializer.instance.completed_at)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(hospitalization, "branch", None),
                cabinet=getattr(hospitalization, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))

        if status_value == HospitalProcedurePlan.PlanStatus.DONE and completed_at is None:
            serializer.save(
                completed_at=timezone.now(),
                completed_by=completed_by or (self.request.user if self.request.user.is_authenticated else None),
            )
            return
        serializer.save()


class MedicationAdministrationViewSet(RBACModelViewSet):
    queryset = MedicationAdministration.objects.select_related(
        "prescription",
        "prescription__visit",
        "given_by",
        "inventory_item",
        "batch",
    ).all()
    serializer_class = MedicationAdministrationSerializer
    scope_branch_field = "prescription__visit__branch"
    scope_cabinet_field = "prescription__visit__cabinet"
    filterset_fields = ["prescription", "status", "inventory_item", "given_by"]
    search_fields = ["prescription__medication_name", "deviation_note", "write_off_note"]

    def perform_create(self, serializer):
        prescription = serializer.validated_data.get("prescription")
        visit = getattr(prescription, "visit", None)
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
        prescription = serializer.validated_data.get("prescription", serializer.instance.prescription)
        visit = getattr(prescription, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(visit, "branch", None),
                cabinet=getattr(visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="mark-given")
    @transaction.atomic
    def mark_given(self, request, pk=None):
        administration = self.get_object()
        if administration.status != MedicationAdministration.AdministrationStatus.PLANNED:
            return response.Response(
                {"detail": f"administration in status {administration.status} cannot be marked as given"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity_written_off = request.data.get("quantity_written_off")
        write_off_decimal = None
        if quantity_written_off not in (None, ""):
            try:
                write_off_decimal = Decimal(str(quantity_written_off))
            except (InvalidOperation, TypeError):
                return response.Response(
                    {"detail": "quantity_written_off must be a number"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if write_off_decimal < 0:
                return response.Response(
                    {"detail": "quantity_written_off must be non-negative"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        inventory_item = administration.inventory_item
        if request.data.get("inventory_item"):
            from apps.inventory.models import InventoryItem

            inventory_item = InventoryItem.objects.filter(id=request.data["inventory_item"]).first()
            if inventory_item is None:
                return response.Response({"detail": "inventory_item not found"}, status=status.HTTP_400_BAD_REQUEST)
            administration.inventory_item = inventory_item

        if inventory_item is not None and write_off_decimal and write_off_decimal > 0:
            try:
                movements = write_off_inventory_item(
                    item=inventory_item,
                    quantity=write_off_decimal,
                    reason=f"Medication administration #{administration.id}",
                    moved_by=request.user if request.user.is_authenticated else None,
                    reference_type="MedicationAdministration",
                    reference_id=str(administration.id),
                )
            except ValidationError as exc:
                detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
                return response.Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
            administration.quantity_written_off = sum((movement.quantity for movement in movements), Decimal("0"))
            administration.write_off_note = request.data.get("write_off_note", administration.write_off_note)
        elif write_off_decimal is not None:
            administration.quantity_written_off = write_off_decimal

        if request.data.get("dose_amount") not in (None, ""):
            try:
                administration.dose_amount = Decimal(str(request.data["dose_amount"]))
            except (InvalidOperation, TypeError):
                return response.Response({"detail": "dose_amount must be a number"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("dose_unit") not in (None, ""):
            administration.dose_unit = request.data["dose_unit"]
        if request.data.get("route") not in (None, ""):
            administration.route = request.data["route"]
        if request.data.get("deviation_note") not in (None, ""):
            administration.deviation_note = request.data["deviation_note"]

        administration.status = MedicationAdministration.AdministrationStatus.GIVEN
        administration.given_at = timezone.now()
        administration.given_by = request.user if request.user.is_authenticated else None
        administration.save()
        return response.Response(self.get_serializer(administration).data)

    @decorators.action(detail=True, methods=["post"], url_path="mark-skipped")
    @transaction.atomic
    def mark_skipped(self, request, pk=None):
        administration = self.get_object()
        if administration.status == MedicationAdministration.AdministrationStatus.GIVEN:
            return response.Response({"detail": "already given"}, status=status.HTTP_400_BAD_REQUEST)

        administration.status = MedicationAdministration.AdministrationStatus.SKIPPED
        administration.deviation_note = request.data.get("reason", administration.deviation_note)
        administration.save(update_fields=["status", "deviation_note", "updated_at"])
        return response.Response(self.get_serializer(administration).data)

    @decorators.action(detail=True, methods=["post"], url_path="mark-canceled")
    @transaction.atomic
    def mark_canceled(self, request, pk=None):
        administration = self.get_object()
        if administration.status == MedicationAdministration.AdministrationStatus.GIVEN:
            return response.Response({"detail": "already given"}, status=status.HTTP_400_BAD_REQUEST)

        administration.status = MedicationAdministration.AdministrationStatus.CANCELED
        administration.deviation_note = request.data.get("reason", administration.deviation_note)
        administration.save(update_fields=["status", "deviation_note", "updated_at"])
        return response.Response(self.get_serializer(administration).data)
