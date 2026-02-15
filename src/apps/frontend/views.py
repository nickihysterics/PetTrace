from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.labs.models import LabOrder, LabResultValue, LabTest, Specimen
from apps.labs.services import sync_lab_order_status
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.tasks.models import Task
from apps.users.access import restrict_queryset_for_user_scope
from apps.visits.models import Appointment, Visit

from .forms import (
    AppointmentCreateForm,
    DiagnosisCreateForm,
    FrontendAuthenticationForm,
    OwnerForm,
    PetForm,
    PrescriptionCreateForm,
    ProcedureCreateForm,
    VisitUpdateForm,
)
from .services import (
    check_in_appointment,
    complete_appointment,
    start_visit_from_appointment,
    transition_appointment_status,
    transition_lab_order,
    transition_specimen,
    transition_visit_status,
)


class FrontendLoginView(LoginView):
    template_name = "frontend/login.html"
    authentication_form = FrontendAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("frontend:role-home")


class FrontendLogoutView(LogoutView):
    next_page = "frontend:login"


def _ensure_perm(user, perm: str):
    if not user.has_perm(perm):
        raise PermissionDenied


def _parse_selected_date(raw: str | None) -> date:
    if not raw:
        return timezone.localdate()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return timezone.localdate()


def _redirect_with_query(view_name: str, **params):
    base_url = reverse(view_name)
    filtered = {key: value for key, value in params.items() if value not in ("", None)}
    if not filtered:
        return redirect(base_url)
    return redirect(f"{base_url}?{urlencode(filtered)}")


def _choice_labels(model, field_name: str) -> dict[str, str]:
    field = model._meta.get_field(field_name)
    return {str(value): str(label) for value, label in field.choices}


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("frontend:role-home")
    return redirect("frontend:login")


@login_required
def dashboard(request):
    now = timezone.now()
    today = timezone.localdate()

    appointments_today = None
    queue_waiting = None
    in_progress_visits = None
    open_lab_orders = None
    overdue_tasks = None

    if request.user.has_perm("visits.view_appointment"):
        scoped_appointments = restrict_queryset_for_user_scope(
            queryset=Appointment.objects.all(),
            user=request.user,
            branch_field="branch",
            cabinet_field="cabinet",
        )
        appointments_today = scoped_appointments.filter(start_at__date=today).count()
        queue_waiting = scoped_appointments.filter(
            start_at__date=today,
            status__in=[
                Appointment.AppointmentStatus.CHECKED_IN,
                Appointment.AppointmentStatus.IN_ROOM,
            ],
        ).count()

    if request.user.has_perm("visits.view_visit"):
        scoped_visits = restrict_queryset_for_user_scope(
            queryset=Visit.objects.all(),
            user=request.user,
            branch_field="branch",
            cabinet_field="cabinet",
        )
        in_progress_visits = scoped_visits.filter(status=Visit.VisitStatus.IN_PROGRESS).count()

    if request.user.has_perm("labs.view_laborder"):
        scoped_orders = restrict_queryset_for_user_scope(
            queryset=LabOrder.objects.all(),
            user=request.user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
        open_lab_orders = scoped_orders.filter(
            status__in=[
                LabOrder.LabOrderStatus.PLANNED,
                LabOrder.LabOrderStatus.COLLECTED,
                LabOrder.LabOrderStatus.IN_TRANSPORT,
                LabOrder.LabOrderStatus.RECEIVED,
                LabOrder.LabOrderStatus.IN_PROCESS,
            ]
        ).count()

    if request.user.has_perm("tasks.view_task"):
        base_tasks = Task.objects.all()
        scoped_visit_tasks = restrict_queryset_for_user_scope(
            queryset=base_tasks.filter(visit__isnull=False),
            user=request.user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
        scoped_lab_tasks = restrict_queryset_for_user_scope(
            queryset=base_tasks.filter(visit__isnull=True, lab_order__isnull=False),
            user=request.user,
            branch_field="lab_order__visit__branch",
            cabinet_field="lab_order__visit__cabinet",
        )
        detached_tasks = base_tasks.filter(visit__isnull=True, lab_order__isnull=True)
        scoped_tasks = (scoped_visit_tasks | scoped_lab_tasks | detached_tasks).distinct()

        overdue_tasks = scoped_tasks.filter(
            status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS],
            due_at__lt=now,
        ).count()

    recent_visits = []
    if request.user.has_perm("visits.view_visit"):
        scoped_visits = restrict_queryset_for_user_scope(
            queryset=Visit.objects.select_related("pet", "owner", "veterinarian"),
            user=request.user,
            branch_field="branch",
            cabinet_field="cabinet",
        )
        recent_visits = list(
            scoped_visits.order_by("-created_at")[:10]
        )

    today_orders = []
    if request.user.has_perm("labs.view_laborder"):
        scoped_today_orders = restrict_queryset_for_user_scope(
            queryset=LabOrder.objects.select_related("visit__pet", "visit__owner"),
            user=request.user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
        today_orders = list(
            scoped_today_orders.filter(ordered_at__date=today)
            .order_by("-ordered_at")[:10]
        )

    context = {
        "today": today,
        "appointments_today": appointments_today,
        "queue_waiting": queue_waiting,
        "in_progress_visits": in_progress_visits,
        "open_lab_orders": open_lab_orders,
        "overdue_tasks": overdue_tasks,
        "recent_visits": recent_visits,
        "today_orders": today_orders,
    }
    return render(request, "frontend/dashboard.html", context)


@login_required
def owners_list(request):
    _ensure_perm(request.user, "owners.view_owner")
    query = (request.GET.get("q") or "").strip()

    owners_qs = Owner.objects.select_related("preferred_branch").all()
    if query:
        owners_qs = owners_qs.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )

    owners = owners_qs.order_by("last_name", "first_name")[:200]
    return render(
        request,
        "frontend/owners_list.html",
        {"owners": owners, "query": query},
    )


@login_required
def owner_create(request):
    _ensure_perm(request.user, "owners.add_owner")
    form = OwnerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        owner = form.save()
        messages.success(request, f"Владелец '{owner}' создан.")
        return redirect("frontend:owners-list")
    return render(request, "frontend/owner_form.html", {"form": form})


@login_required
def pets_list(request):
    _ensure_perm(request.user, "pets.view_pet")
    query = (request.GET.get("q") or "").strip()

    pets_qs = Pet.objects.select_related("owner").all()
    if query:
        pets_qs = pets_qs.filter(
            Q(name__icontains=query)
            | Q(microchip_id__icontains=query)
            | Q(owner__first_name__icontains=query)
            | Q(owner__last_name__icontains=query)
            | Q(owner__phone__icontains=query)
        )

    pets = pets_qs.order_by("name")[:300]
    return render(
        request,
        "frontend/pets_list.html",
        {"pets": pets, "query": query},
    )


@login_required
def pet_create(request):
    _ensure_perm(request.user, "pets.add_pet")
    form = PetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pet = form.save()
        messages.success(request, f"Животное '{pet.name}' добавлено.")
        return redirect("frontend:pets-list")
    return render(request, "frontend/pet_form.html", {"form": form})


@login_required
def appointment_create(request):
    _ensure_perm(request.user, "visits.add_appointment")
    form = AppointmentCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        appointment = form.save(user=request.user)
        messages.success(request, "Запись на прием создана.")
        appointment_date = timezone.localtime(appointment.start_at).date().isoformat()
        return _redirect_with_query("frontend:appointments-board", date=appointment_date)

    return render(request, "frontend/appointment_form.html", {"form": form})


@login_required
def appointments_board(request):
    _ensure_perm(request.user, "visits.view_appointment")
    selected_date = _parse_selected_date(
        request.GET.get("date") or request.POST.get("selected_date")
    )
    scoped_appointments_qs = restrict_queryset_for_user_scope(
        queryset=Appointment.objects.select_related(
            "pet",
            "owner",
            "veterinarian",
            "branch",
            "cabinet",
            "visit",
        ),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )

    if request.method == "POST":
        appointment = get_object_or_404(scoped_appointments_qs, pk=request.POST.get("appointment_id"))
        action = request.POST.get("action")
        try:
            if action == "check_in":
                _ensure_perm(request.user, "visits.change_appointment")
                check_in_appointment(appointment=appointment)
                messages.success(request, f"Запись #{appointment.id}: пациент отмечен.")
            elif action == "start_visit":
                _ensure_perm(request.user, "visits.change_appointment")
                _ensure_perm(request.user, "visits.add_visit")
                chief_complaint = request.POST.get("chief_complaint", "")
                visit = start_visit_from_appointment(
                    appointment=appointment,
                    actor=request.user,
                    chief_complaint=chief_complaint,
                )
                messages.success(request, f"Запущен визит #{visit.id}.")
            elif action == "complete":
                _ensure_perm(request.user, "visits.change_appointment")
                if appointment.visit_id:
                    _ensure_perm(request.user, "visits.change_visit")
                complete_appointment(appointment=appointment, actor=request.user)
                messages.success(request, f"Запись #{appointment.id} завершена.")
            elif action == "transition":
                _ensure_perm(request.user, "visits.change_appointment")
                new_status = request.POST.get("new_status", "")
                transition_appointment_status(appointment=appointment, new_status=new_status)
                messages.success(request, f"Статус записи #{appointment.id} обновлен.")
            else:
                messages.error(request, "Неизвестное действие.")
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:appointments-board", date=selected_date.isoformat())

    status_labels = _choice_labels(Appointment, "status")

    appointments = list(
        scoped_appointments_qs.filter(start_at__date=selected_date)
        .order_by("start_at")
    )
    for appointment in appointments:
        appointment.allowed_transitions = [
            {"code": code, "label": status_labels.get(code, code)}
            for code in sorted(appointment.ALLOWED_TRANSITIONS.get(appointment.status, set()))
        ]

    status_order = [
        Appointment.AppointmentStatus.BOOKED,
        Appointment.AppointmentStatus.CHECKED_IN,
        Appointment.AppointmentStatus.IN_ROOM,
        Appointment.AppointmentStatus.COMPLETED,
        Appointment.AppointmentStatus.NO_SHOW,
        Appointment.AppointmentStatus.CANCELED,
    ]
    columns = []
    for status_code in status_order:
        columns.append(
            {
                "code": status_code,
                "label": status_labels.get(status_code, status_code),
                "items": [item for item in appointments if item.status == status_code],
            }
        )

    return render(
        request,
        "frontend/appointments_board.html",
        {
            "selected_date": selected_date,
            "columns": columns,
        },
    )


@login_required
def visit_detail(request, visit_id: int):
    _ensure_perm(request.user, "visits.view_visit")
    scoped_visits_qs = restrict_queryset_for_user_scope(
        queryset=Visit.objects.select_related(
            "pet",
            "owner",
            "veterinarian",
            "assistant",
            "branch",
            "cabinet",
        ),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )
    visit = get_object_or_404(
        scoped_visits_qs,
        pk=visit_id,
    )

    visit_form = VisitUpdateForm(instance=visit, prefix="visit")
    diagnosis_form = DiagnosisCreateForm(prefix="diagnosis")
    prescription_form = PrescriptionCreateForm(prefix="prescription")
    procedure_form = ProcedureCreateForm(prefix="procedure")

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "update_visit":
                _ensure_perm(request.user, "visits.change_visit")
                visit_form = VisitUpdateForm(request.POST, instance=visit, prefix="visit")
                if visit_form.is_valid():
                    visit_form.save()
                    messages.success(request, "Медицинская часть визита обновлена.")
                else:
                    messages.error(request, "Проверьте форму визита.")
                    return render(
                        request,
                        "frontend/visit_detail.html",
                        _visit_context(
                            request=request,
                            visit=visit,
                            visit_form=visit_form,
                            diagnosis_form=diagnosis_form,
                            prescription_form=prescription_form,
                            procedure_form=procedure_form,
                        ),
                    )
            elif action == "visit_transition":
                _ensure_perm(request.user, "visits.change_visit")
                new_status = request.POST.get("new_status", "")
                if new_status == Visit.VisitStatus.CLOSED:
                    _ensure_perm(request.user, "visits.close_visit")
                notes = request.POST.get("notes", "")
                transition_visit_status(
                    visit=visit,
                    new_status=new_status,
                    actor=request.user,
                    notes=notes,
                )
                messages.success(request, f"Статус визита #{visit.id} обновлен.")
            elif action == "add_diagnosis":
                _ensure_perm(request.user, "visits.add_diagnosis")
                diagnosis_form = DiagnosisCreateForm(request.POST, prefix="diagnosis")
                if diagnosis_form.is_valid():
                    diagnosis = diagnosis_form.save(commit=False)
                    diagnosis.visit = visit
                    diagnosis.save()
                    messages.success(request, "Диагноз добавлен.")
                else:
                    messages.error(request, "Не удалось добавить диагноз.")
                    return render(
                        request,
                        "frontend/visit_detail.html",
                        _visit_context(
                            request=request,
                            visit=visit,
                            visit_form=visit_form,
                            diagnosis_form=diagnosis_form,
                            prescription_form=prescription_form,
                            procedure_form=procedure_form,
                        ),
                    )
            elif action == "add_prescription":
                _ensure_perm(request.user, "visits.add_prescription")
                prescription_form = PrescriptionCreateForm(request.POST, prefix="prescription")
                if prescription_form.is_valid():
                    prescription = prescription_form.save(commit=False)
                    prescription.visit = visit
                    prescription.save()
                    messages.success(request, "Назначение добавлено.")
                else:
                    messages.error(request, "Не удалось добавить назначение.")
                    return render(
                        request,
                        "frontend/visit_detail.html",
                        _visit_context(
                            request=request,
                            visit=visit,
                            visit_form=visit_form,
                            diagnosis_form=diagnosis_form,
                            prescription_form=prescription_form,
                            procedure_form=procedure_form,
                        ),
                    )
            elif action == "add_procedure":
                _ensure_perm(request.user, "visits.add_procedureorder")
                procedure_form = ProcedureCreateForm(request.POST, prefix="procedure")
                if procedure_form.is_valid():
                    procedure = procedure_form.save(commit=False)
                    procedure.visit = visit
                    procedure.performed_by = request.user
                    procedure.save()
                    messages.success(request, "Процедура добавлена.")
                else:
                    messages.error(request, "Не удалось добавить процедуру.")
                    return render(
                        request,
                        "frontend/visit_detail.html",
                        _visit_context(
                            request=request,
                            visit=visit,
                            visit_form=visit_form,
                            diagnosis_form=diagnosis_form,
                            prescription_form=prescription_form,
                            procedure_form=procedure_form,
                        ),
                    )
            else:
                messages.error(request, "Неизвестное действие.")
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)

        return redirect("frontend:visit-detail", visit_id=visit.id)

    return render(
        request,
        "frontend/visit_detail.html",
        _visit_context(
            request=request,
            visit=visit,
            visit_form=visit_form,
            diagnosis_form=diagnosis_form,
            prescription_form=prescription_form,
            procedure_form=procedure_form,
        ),
    )


def _visit_context(
    *,
    request,
    visit: Visit,
    visit_form: VisitUpdateForm,
    diagnosis_form: DiagnosisCreateForm,
    prescription_form: PrescriptionCreateForm,
    procedure_form: ProcedureCreateForm,
):
    visit_status_labels = _choice_labels(Visit, "status")
    visit_transition_options = [
        {"code": code, "label": visit_status_labels.get(code, code)}
        for code in sorted(visit.ALLOWED_TRANSITIONS.get(visit.status, set()))
    ]

    visit_events = list(visit.events.select_related("actor").all()[:20])
    for event in visit_events:
        event.from_status_label = visit_status_labels.get(event.from_status, event.from_status)
        event.to_status_label = visit_status_labels.get(event.to_status, event.to_status)

    return {
        "visit": visit,
        "visit_form": visit_form,
        "diagnosis_form": diagnosis_form,
        "prescription_form": prescription_form,
        "procedure_form": procedure_form,
        "visit_transition_options": visit_transition_options,
        "diagnoses": list(visit.diagnoses.all()),
        "prescriptions": list(visit.prescriptions.all()),
        "procedures": list(visit.procedures.all()),
        "visit_events": visit_events,
        "lab_orders": list(visit.lab_orders.all()[:20]),
        "can_view_clinical_alerts": request.user.has_perm("clinical.view_clinicalalert"),
        "clinical_alerts": list(
            visit.clinical_alerts.filter(resolved_at__isnull=True).select_related("rule").all()[:20]
        ),
    }


@login_required
def labs_board(request):
    _ensure_perm(request.user, "labs.view_laborder")
    status_filter = (request.GET.get("status") or request.POST.get("status_filter") or "").strip()
    scoped_orders_qs = restrict_queryset_for_user_scope(
        queryset=LabOrder.objects.select_related("visit__pet", "visit__owner", "ordered_by").prefetch_related(
            "specimens",
            "tests",
        ),
        user=request.user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )
    scoped_specimens_qs = restrict_queryset_for_user_scope(
        queryset=Specimen.objects.select_related("lab_order__visit"),
        user=request.user,
        branch_field="lab_order__visit__branch",
        cabinet_field="lab_order__visit__cabinet",
    )
    scoped_results_qs = restrict_queryset_for_user_scope(
        queryset=LabResultValue.objects.select_related("lab_test__lab_order__visit__pet"),
        user=request.user,
        branch_field="lab_test__lab_order__visit__branch",
        cabinet_field="lab_test__lab_order__visit__cabinet",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "order_transition":
                _ensure_perm(request.user, "labs.change_laborder")
                order = get_object_or_404(scoped_orders_qs, pk=request.POST.get("order_id"))
                transition_lab_order(
                    order=order,
                    new_status=request.POST.get("new_status", ""),
                    actor=request.user,
                    location=request.POST.get("location", ""),
                    notes=request.POST.get("notes", ""),
                )
                messages.success(request, f"Статус заказа #{order.id} обновлен.")
            elif action == "specimen_transition":
                _ensure_perm(request.user, "labs.change_specimen")
                specimen = get_object_or_404(scoped_specimens_qs, pk=request.POST.get("specimen_id"))
                transition_specimen(
                    specimen=specimen,
                    new_status=request.POST.get("new_status", ""),
                    actor=request.user,
                    location=request.POST.get("location", ""),
                    notes=request.POST.get("notes", ""),
                )
                messages.success(request, f"Статус образца #{specimen.id} обновлен.")
            elif action == "approve_result":
                _ensure_perm(request.user, "labs.approve_lab_result")
                result = get_object_or_404(scoped_results_qs, pk=request.POST.get("result_id"))
                if result.approved_at is None:
                    result.approved_by = request.user
                    result.approved_at = timezone.now()
                    result.approval_note = request.POST.get("approval_note", "")
                    result.save(
                        update_fields=["approved_by", "approved_at", "approval_note", "updated_at"]
                    )
                    if result.lab_test.status != LabTest.LabTestStatus.DONE:
                        result.lab_test.status = LabTest.LabTestStatus.DONE
                        result.lab_test.save(update_fields=["status", "updated_at"])
                    sync_lab_order_status(result.lab_test.lab_order)
                    messages.success(request, f"Результат #{result.id} утвержден.")
                else:
                    messages.info(request, f"Результат #{result.id} уже утвержден.")
            else:
                messages.error(request, "Неизвестное действие.")
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:labs-board", status=status_filter)

    order_status_labels = _choice_labels(LabOrder, "status")
    specimen_status_labels = _choice_labels(Specimen, "status")

    orders_qs = scoped_orders_qs.order_by("-ordered_at")
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
    orders = list(orders_qs[:60])

    for order in orders:
        order.allowed_transitions = [
            {"code": code, "label": order_status_labels.get(code, code)}
            for code in sorted(order.ALLOWED_TRANSITIONS.get(order.status, set()))
        ]
        order.specimens_for_ui = list(order.specimens.all())
        for specimen in order.specimens_for_ui:
            specimen.allowed_transitions = [
                {"code": code, "label": specimen_status_labels.get(code, code)}
                for code in sorted(specimen.ALLOWED_TRANSITIONS.get(specimen.status, set()))
            ]

    pending_results = []
    if request.user.has_perm("labs.view_labresultvalue"):
        pending_results = list(
            scoped_results_qs.filter(approved_at__isnull=True)
            .order_by("-created_at")[:30]
        )

    status_choices = list(order_status_labels.items())

    return render(
        request,
        "frontend/labs_board.html",
        {
            "orders": orders,
            "pending_results": pending_results,
            "status_filter": status_filter,
            "status_choices": status_choices,
        },
    )
