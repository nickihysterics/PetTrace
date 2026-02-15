from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import Invoice, Payment, PaymentAdjustment
from apps.inventory.models import Batch, InventoryItem, StockMovement
from apps.labs.models import LabOrder, LabResultValue, Specimen
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.tasks.models import Task
from apps.users.access import (
    get_user_role_names,
    is_unrestricted_user,
    restrict_queryset_for_user_scope,
)
from apps.visits.models import (
    Appointment,
    Hospitalization,
    MedicationAdministration,
    ProcedureOrder,
    Visit,
)

ROLE_HOME_ORDER = [
    "administrator",
    "registrar",
    "veterinarian",
    "assistant",
    "lab_technician",
    "inventory_manager",
    "cashier",
]

ROLE_HOME_META = {
    "administrator": {
        "title": "Кабинет администратора",
        "subtitle": "Контроль операционного контура и системных показателей.",
    },
    "registrar": {
        "title": "Кабинет регистратора",
        "subtitle": "Запись, очередь, CRM и операционная координация.",
    },
    "veterinarian": {
        "title": "Кабинет врача",
        "subtitle": "Клиническая работа, стационар и контроль назначений.",
    },
    "assistant": {
        "title": "Кабинет ассистента",
        "subtitle": "Исполнение процедур, лабораторных задач и MAR.",
    },
    "lab_technician": {
        "title": "Кабинет лаборанта",
        "subtitle": "Лабораторный pipeline и результаты анализов.",
    },
    "inventory_manager": {
        "title": "Кабинет склада",
        "subtitle": "Остатки, партии, сроки и списания.",
    },
    "cashier": {
        "title": "Кабинет кассира",
        "subtitle": "Счета, оплаты и корректировки платежей.",
    },
}


def _scoped_appointments(user):
    return restrict_queryset_for_user_scope(
        queryset=Appointment.objects.select_related("pet", "owner", "cabinet", "visit"),
        user=user,
        branch_field="branch",
        cabinet_field="cabinet",
    )


def _scoped_visits(user):
    return restrict_queryset_for_user_scope(
        queryset=Visit.objects.select_related("pet", "owner", "veterinarian", "cabinet"),
        user=user,
        branch_field="branch",
        cabinet_field="cabinet",
    )


def _scoped_lab_orders(user):
    return restrict_queryset_for_user_scope(
        queryset=LabOrder.objects.select_related("visit", "visit__pet", "visit__owner"),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )


def _scoped_hospitalizations(user):
    return restrict_queryset_for_user_scope(
        queryset=Hospitalization.objects.select_related("visit", "visit__pet", "current_bed", "branch"),
        user=user,
        branch_field="branch",
        cabinet_field="cabinet",
    )


def _scoped_medications(user):
    return restrict_queryset_for_user_scope(
        queryset=MedicationAdministration.objects.select_related(
            "prescription",
            "prescription__visit",
            "prescription__visit__pet",
            "inventory_item",
            "given_by",
        ),
        user=user,
        branch_field="prescription__visit__branch",
        cabinet_field="prescription__visit__cabinet",
    )


def _scoped_invoices(user):
    return restrict_queryset_for_user_scope(
        queryset=Invoice.objects.select_related("visit", "visit__pet", "visit__owner"),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )


def _scoped_payments(user):
    return restrict_queryset_for_user_scope(
        queryset=Payment.objects.select_related("invoice", "invoice__visit", "invoice__visit__pet"),
        user=user,
        branch_field="invoice__visit__branch",
        cabinet_field="invoice__visit__cabinet",
    )


def _scoped_payment_adjustments(user):
    return restrict_queryset_for_user_scope(
        queryset=PaymentAdjustment.objects.select_related(
            "payment",
            "payment__invoice",
            "payment__invoice__visit",
            "payment__invoice__visit__pet",
        ),
        user=user,
        branch_field="payment__invoice__visit__branch",
        cabinet_field="payment__invoice__visit__cabinet",
    )


def _scoped_procedures(user):
    return restrict_queryset_for_user_scope(
        queryset=ProcedureOrder.objects.select_related("visit", "visit__pet", "performed_by"),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )


def _scoped_specimens(user):
    return restrict_queryset_for_user_scope(
        queryset=Specimen.objects.select_related("lab_order", "lab_order__visit", "lab_order__visit__pet"),
        user=user,
        branch_field="lab_order__visit__branch",
        cabinet_field="lab_order__visit__cabinet",
    )


def _scoped_lab_results(user):
    return restrict_queryset_for_user_scope(
        queryset=LabResultValue.objects.select_related(
            "lab_test",
            "lab_test__lab_order",
            "lab_test__lab_order__visit",
            "lab_test__lab_order__visit__pet",
        ),
        user=user,
        branch_field="lab_test__lab_order__visit__branch",
        cabinet_field="lab_test__lab_order__visit__cabinet",
    )


def _scoped_tasks(user):
    base_tasks = Task.objects.select_related("visit", "visit__pet", "lab_order")
    visit_tasks = restrict_queryset_for_user_scope(
        queryset=base_tasks.filter(visit__isnull=False),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )
    lab_tasks = restrict_queryset_for_user_scope(
        queryset=base_tasks.filter(visit__isnull=True, lab_order__isnull=False),
        user=user,
        branch_field="lab_order__visit__branch",
        cabinet_field="lab_order__visit__cabinet",
    )
    detached = base_tasks.filter(visit__isnull=True, lab_order__isnull=True)
    return (visit_tasks | lab_tasks | detached).distinct()


def _row(title: str, meta: str, *, url: str = "") -> dict[str, str]:
    return {"title": title, "meta": meta, "url": url}


def _panel(title: str, rows: list[dict[str, str]]) -> dict:
    return {"title": title, "rows": rows}


def _quick_link(user, title: str, url_name: str, perm: str | None = None):
    if perm and not user.has_perm(perm):
        return None
    return {"title": title, "url": reverse(url_name)}


def _clean_links(items: list[dict | None]) -> list[dict]:
    return [item for item in items if item is not None]


def _primary_role(user) -> str:
    if is_unrestricted_user(user):
        return "administrator"
    role_names = set(get_user_role_names(user))
    for role in ROLE_HOME_ORDER:
        if role in role_names:
            return role
    return "registrar"


def _available_roles(user) -> list[str]:
    if is_unrestricted_user(user):
        return ROLE_HOME_ORDER.copy()
    role_names = set(get_user_role_names(user))
    roles = [role for role in ROLE_HOME_ORDER if role in role_names]
    return roles or [_primary_role(user)]


def _build_admin_context(user, now, today):
    del now, today
    visits = _scoped_visits(user)
    orders = _scoped_lab_orders(user)
    invoices = _scoped_invoices(user)
    results = _scoped_lab_results(user)

    unpaid_statuses = [Invoice.InvoiceStatus.FORMED, Invoice.InvoiceStatus.POSTED]
    open_order_statuses = [
        LabOrder.LabOrderStatus.PLANNED,
        LabOrder.LabOrderStatus.COLLECTED,
        LabOrder.LabOrderStatus.IN_TRANSPORT,
        LabOrder.LabOrderStatus.RECEIVED,
        LabOrder.LabOrderStatus.IN_PROCESS,
    ]
    unpaid_total = invoices.filter(status__in=unpaid_statuses).aggregate(total=Sum("total_amount"))[
        "total"
    ] or Decimal("0")
    critical_pending = results.filter(flag=LabResultValue.Flag.CRITICAL, approved_at__isnull=True)

    kpis = [
        {
            "label": "Визиты в работе",
            "value": visits.filter(status=Visit.VisitStatus.IN_PROGRESS).count(),
            "note": "",
        },
        {
            "label": "Лаборатория в процессе",
            "value": orders.filter(status__in=open_order_statuses).count(),
            "note": "",
        },
        {
            "label": "Счетов к оплате",
            "value": invoices.filter(status__in=unpaid_statuses).count(),
            "note": f"Сумма: {unpaid_total}",
        },
        {
            "label": "Критические результаты",
            "value": critical_pending.count(),
            "note": "Ожидают реакции",
        },
    ]

    panels = [
        _panel(
            "Последние визиты",
            [
                _row(
                    f"#{visit.id} · {visit.pet.name}",
                    f"{visit.get_status_display()} · {timezone.localtime(visit.created_at).strftime('%d.%m %H:%M')}",
                    url=(
                        reverse("frontend:visit-detail", kwargs={"visit_id": visit.id})
                        if user.has_perm("visits.view_visit")
                        else ""
                    ),
                )
                for visit in visits.order_by("-created_at")[:8]
            ],
        ),
        _panel(
            "Счета к оплате",
            [
                _row(
                    f"Счет #{invoice.id} · {invoice.visit.pet.name}",
                    f"{invoice.get_status_display()} · к оплате {invoice.total_amount}",
                )
                for invoice in invoices.filter(status__in=unpaid_statuses).order_by("-created_at")[:8]
            ],
        ),
        _panel(
            "Критические лабораторные результаты",
            [
                _row(
                    f"{result.lab_test.lab_order.visit.pet.name} · {result.parameter_name}",
                    f"{result.value} {result.unit} · заказ #{result.lab_test.lab_order_id}",
                )
                for result in critical_pending.order_by("-created_at")[:8]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Ролевые кабинеты", "frontend:role-cabinets"),
            _quick_link(user, "Приемы", "frontend:appointments-board", "visits.view_appointment"),
            _quick_link(user, "Лаборатория", "frontend:labs-board", "labs.view_laborder"),
            _quick_link(user, "Финансы", "frontend:finance-board", "billing.view_invoice"),
            _quick_link(
                user,
                "Документы",
                "frontend:documents-board",
                "documents.view_clinicaldocument",
            ),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_registrar_context(user, now, today):
    appointments = _scoped_appointments(user)
    today_appointments = appointments.filter(start_at__date=today)

    queue_statuses = [
        Appointment.AppointmentStatus.BOOKED,
        Appointment.AppointmentStatus.CHECKED_IN,
        Appointment.AppointmentStatus.IN_ROOM,
    ]
    upcoming_window_end = now + timedelta(hours=4)

    owners_total = Owner.objects.count() if user.has_perm("owners.view_owner") else None
    pets_total = Pet.objects.count() if user.has_perm("pets.view_pet") else None

    kpis = [
        {"label": "Приемов сегодня", "value": today_appointments.count(), "note": ""},
        {
            "label": "В живой очереди",
            "value": today_appointments.filter(status__in=queue_statuses).count(),
            "note": "",
        },
        {
            "label": "Владельцев в базе",
            "value": owners_total if owners_total is not None else "-",
            "note": "",
        },
        {
            "label": "Животных в базе",
            "value": pets_total if pets_total is not None else "-",
            "note": "",
        },
    ]

    queue_rows = []
    for appointment in today_appointments.filter(status__in=queue_statuses).order_by("start_at")[:10]:
        queue_rows.append(
            _row(
                f"{timezone.localtime(appointment.start_at).strftime('%H:%M')} · {appointment.pet.name}",
                f"{appointment.get_status_display()} · #{appointment.id}",
                url=(
                    reverse("frontend:visit-detail", kwargs={"visit_id": appointment.visit_id})
                    if appointment.visit_id and user.has_perm("visits.view_visit")
                    else ""
                ),
            )
        )

    upcoming_rows = [
        _row(
            f"{timezone.localtime(appointment.start_at).strftime('%H:%M')} · {appointment.pet.name}",
            f"{appointment.owner.last_name} {appointment.owner.first_name}",
        )
        for appointment in appointments.filter(start_at__gte=now, start_at__lte=upcoming_window_end)
        .order_by("start_at")[:10]
    ]

    owners_rows = []
    if user.has_perm("owners.view_owner"):
        owners_rows = [
            _row(
                f"{owner.last_name} {owner.first_name}",
                owner.phone or owner.email or "Без контакта",
            )
            for owner in Owner.objects.order_by("-created_at")[:10]
        ]

    panels = [
        _panel("Очередь на сегодня", queue_rows),
        _panel("Ближайшие записи (4 часа)", upcoming_rows),
        _panel("Новые владельцы", owners_rows),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Запись на прием", "frontend:appointment-create", "visits.add_appointment"),
            _quick_link(user, "Табло приемов", "frontend:appointments-board", "visits.view_appointment"),
            _quick_link(user, "Владельцы", "frontend:owners-list", "owners.view_owner"),
            _quick_link(user, "Животные", "frontend:pets-list", "pets.view_pet"),
            _quick_link(user, "Документы", "frontend:documents-board", "documents.view_clinicaldocument"),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_veterinarian_context(user, now, today):
    del now, today
    visits = _scoped_visits(user).filter(veterinarian=user)
    hospitalizations = _scoped_hospitalizations(user).filter(
        status__in=[
            Hospitalization.HospitalizationStatus.ADMITTED,
            Hospitalization.HospitalizationStatus.UNDER_OBSERVATION,
            Hospitalization.HospitalizationStatus.CRITICAL,
        ]
    )
    orders = _scoped_lab_orders(user).filter(visit__veterinarian=user)
    results = _scoped_lab_results(user).filter(
        lab_test__lab_order__visit__veterinarian=user,
        approved_at__isnull=True,
    )

    open_order_statuses = [
        LabOrder.LabOrderStatus.PLANNED,
        LabOrder.LabOrderStatus.COLLECTED,
        LabOrder.LabOrderStatus.IN_TRANSPORT,
        LabOrder.LabOrderStatus.RECEIVED,
        LabOrder.LabOrderStatus.IN_PROCESS,
    ]

    kpis = [
        {
            "label": "Мои визиты в работе",
            "value": visits.filter(status=Visit.VisitStatus.IN_PROGRESS).count(),
            "note": "",
        },
        {"label": "Пациенты стационара", "value": hospitalizations.count(), "note": ""},
        {
            "label": "Мои лаб-заказы в работе",
            "value": orders.filter(status__in=open_order_statuses).count(),
            "note": "",
        },
        {"label": "Результаты к просмотру", "value": results.count(), "note": ""},
    ]

    panels = [
        _panel(
            "Мои активные визиты",
            [
                _row(
                    f"#{visit.id} · {visit.pet.name}",
                    f"{visit.get_status_display()} · {visit.owner.last_name} {visit.owner.first_name}",
                    url=(
                        reverse("frontend:visit-detail", kwargs={"visit_id": visit.id})
                        if user.has_perm("visits.view_visit")
                        else ""
                    ),
                )
                for visit in visits.filter(
                    status__in=[
                        Visit.VisitStatus.WAITING,
                        Visit.VisitStatus.IN_PROGRESS,
                        Visit.VisitStatus.COMPLETED,
                    ]
                )
                .order_by("-created_at")[:10]
            ],
        ),
        _panel(
            "Пациенты стационара",
            [
                _row(
                    f"{hospitalization.visit.pet.name} · госпит. #{hospitalization.id}",
                    (
                        f"{hospitalization.get_status_display()} · "
                        f"{hospitalization.current_bed.code if hospitalization.current_bed else 'без койки'}"
                    ),
                )
                for hospitalization in hospitalizations.order_by("-admitted_at")[:10]
            ],
        ),
        _panel(
            "Критические результаты",
            [
                _row(
                    f"{result.lab_test.lab_order.visit.pet.name} · {result.parameter_name}",
                    f"{result.value} {result.unit} · флаг {result.get_flag_display()}",
                )
                for result in results.filter(flag=LabResultValue.Flag.CRITICAL).order_by("-created_at")[:10]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Приемы", "frontend:appointments-board", "visits.view_appointment"),
            _quick_link(user, "Стационар", "frontend:hospitalization-board", "visits.view_hospitalization"),
            _quick_link(user, "MAR", "frontend:mar-board", "visits.view_medicationadministration"),
            _quick_link(user, "Лаборатория", "frontend:labs-board", "labs.view_laborder"),
            _quick_link(user, "Финансы", "frontend:finance-board", "billing.view_invoice"),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_assistant_context(user, now, today):
    procedures = _scoped_procedures(user)
    medications = _scoped_medications(user)
    hospitalizations = _scoped_hospitalizations(user).filter(
        status__in=[
            Hospitalization.HospitalizationStatus.ADMITTED,
            Hospitalization.HospitalizationStatus.UNDER_OBSERVATION,
            Hospitalization.HospitalizationStatus.CRITICAL,
        ]
    )
    tasks = _scoped_tasks(user)
    mar_window_end = now + timedelta(hours=6)

    kpis = [
        {
            "label": "Процедуры к выполнению",
            "value": procedures.filter(
                status__in=[
                    ProcedureOrder.ProcedureStatus.PLANNED,
                    ProcedureOrder.ProcedureStatus.IN_PROGRESS,
                ]
            ).count(),
            "note": "",
        },
        {
            "label": "MAR на 6 часов",
            "value": medications.filter(
                status=MedicationAdministration.AdministrationStatus.PLANNED,
                scheduled_at__gte=now,
                scheduled_at__lte=mar_window_end,
            ).count(),
            "note": "",
        },
        {"label": "Пациенты стационара", "value": hospitalizations.count(), "note": ""},
        {
            "label": "Задачи в работе",
            "value": tasks.filter(
                status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS]
            ).count(),
            "note": "",
        },
    ]

    panels = [
        _panel(
            "Процедуры",
            [
                _row(
                    f"{procedure.visit.pet.name} · {procedure.name}",
                    f"{procedure.get_status_display()} · визит #{procedure.visit_id}",
                )
                for procedure in procedures.filter(
                    status__in=[
                        ProcedureOrder.ProcedureStatus.PLANNED,
                        ProcedureOrder.ProcedureStatus.IN_PROGRESS,
                    ]
                )
                .order_by("-created_at")[:10]
            ],
        ),
        _panel(
            "MAR: ближайшие введения",
            [
                _row(
                    (
                        f"{timezone.localtime(administration.scheduled_at).strftime('%d.%m %H:%M')} · "
                        f"{administration.prescription.visit.pet.name}"
                    ),
                    (
                        f"{administration.prescription.medication_name} · "
                        f"{administration.get_status_display()}"
                    ),
                )
                for administration in medications.filter(
                    status=MedicationAdministration.AdministrationStatus.PLANNED,
                    scheduled_at__gte=now,
                    scheduled_at__lte=mar_window_end,
                )
                .order_by("scheduled_at")[:10]
            ],
        ),
        _panel(
            "Лабораторные задачи",
            [
                _row(
                    task.title,
                    (
                        f"{task.get_status_display()} · до "
                        f"{timezone.localtime(task.due_at).strftime('%d.%m %H:%M') if task.due_at else '-'}"
                    ),
                )
                for task in tasks.filter(
                    task_type__in=[Task.TaskType.COLLECT_SPECIMEN, Task.TaskType.LAB_RECEIVE],
                    status__in=[Task.TaskStatus.TODO, Task.TaskStatus.IN_PROGRESS],
                )
                .order_by("due_at", "-created_at")[:10]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Приемы", "frontend:appointments-board", "visits.view_appointment"),
            _quick_link(user, "Стационар", "frontend:hospitalization-board", "visits.view_hospitalization"),
            _quick_link(user, "MAR", "frontend:mar-board", "visits.view_medicationadministration"),
            _quick_link(user, "Лаборатория", "frontend:labs-board", "labs.view_laborder"),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_lab_context(user, now, today):
    del now
    orders = _scoped_lab_orders(user)
    specimens = _scoped_specimens(user)
    results = _scoped_lab_results(user)

    open_order_statuses = [
        LabOrder.LabOrderStatus.COLLECTED,
        LabOrder.LabOrderStatus.IN_TRANSPORT,
        LabOrder.LabOrderStatus.RECEIVED,
        LabOrder.LabOrderStatus.IN_PROCESS,
    ]
    kpis = [
        {
            "label": "Заказы в работе",
            "value": orders.filter(status__in=open_order_statuses).count(),
            "note": "",
        },
        {
            "label": "Результаты к утверждению",
            "value": results.filter(approved_at__isnull=True).count(),
            "note": "",
        },
        {
            "label": "Отклоненные образцы сегодня",
            "value": specimens.filter(
                status=Specimen.SpecimenStatus.REJECTED,
                done_at__date=today,
            ).count(),
            "note": "",
        },
        {
            "label": "Критические результаты",
            "value": results.filter(
                flag=LabResultValue.Flag.CRITICAL,
                approved_at__isnull=True,
            ).count(),
            "note": "",
        },
    ]

    panels = [
        _panel(
            "Заказы в работе",
            [
                _row(
                    f"#{order.id} · {order.visit.pet.name}",
                    f"{order.get_status_display()} · SLA {order.sla_minutes} мин",
                )
                for order in orders.filter(status__in=open_order_statuses).order_by("-ordered_at")[:10]
            ],
        ),
        _panel(
            "Неутвержденные результаты",
            [
                _row(
                    f"{result.lab_test.lab_order.visit.pet.name} · {result.parameter_name}",
                    f"{result.value} {result.unit} · {result.get_flag_display()}",
                )
                for result in results.filter(approved_at__isnull=True).order_by("-created_at")[:10]
            ],
        ),
        _panel(
            "Отклоненные образцы",
            [
                _row(
                    f"#{specimen.id} · {specimen.lab_order.visit.pet.name}",
                    (
                        f"{specimen.specimen_type} · причина "
                        f"{specimen.get_rejection_reason_display() or '-'}"
                    ),
                )
                for specimen in specimens.filter(status=Specimen.SpecimenStatus.REJECTED).order_by("-done_at")[:10]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Лаборатория", "frontend:labs-board", "labs.view_laborder"),
            _quick_link(user, "Документы", "frontend:documents-board", "documents.view_clinicaldocument"),
            _quick_link(user, "Дашборд", "frontend:dashboard"),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_inventory_context(user, now, today):
    del user, now
    low_stock = list(
        InventoryItem.objects.filter(is_active=True)
        .annotate(stock=Coalesce(Sum("batches__quantity_available"), Decimal("0")))
        .filter(stock__lte=models.F("min_stock"))
        .order_by("stock", "name")[:10]
    )
    expiring = list(
        Batch.objects.select_related("item")
        .filter(
            quantity_available__gt=0,
            expires_at__isnull=False,
            expires_at__lte=today + timedelta(days=30),
        )
        .order_by("expires_at", "item__name")[:10]
    )
    write_off_today_qs = StockMovement.objects.select_related("item").filter(
        movement_type=StockMovement.MovementType.WRITE_OFF,
        created_at__date=today,
    )
    write_off_total = write_off_today_qs.aggregate(total=Sum("quantity"))["total"] or Decimal("0")

    kpis = [
        {"label": "Низкий остаток", "value": len(low_stock), "note": ""},
        {"label": "Партии с истечением <=30д", "value": len(expiring), "note": ""},
        {"label": "Списано сегодня", "value": write_off_total, "note": ""},
        {"label": "Операций списания", "value": write_off_today_qs.count(), "note": ""},
    ]

    panels = [
        _panel(
            "Низкий остаток",
            [
                _row(
                    f"{item.name} ({item.sku})",
                    f"Остаток {item.stock} {item.unit} · минимум {item.min_stock}",
                )
                for item in low_stock
            ],
        ),
        _panel(
            "Скорое истечение партий",
            [
                _row(
                    f"{batch.item.name} · {batch.lot_number}",
                    (
                        f"Годен до {batch.expires_at.strftime('%d.%m.%Y')} · "
                        f"в наличии {batch.quantity_available}"
                    ),
                )
                for batch in expiring
            ],
        ),
        _panel(
            "Последние списания",
            [
                _row(
                    f"{movement.item.name}",
                    f"{movement.quantity} {movement.item.unit} · {movement.reason or '-'}",
                )
                for movement in write_off_today_qs.order_by("-created_at")[:10]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            {"title": "MAR", "url": reverse("frontend:mar-board")},
            {"title": "Дашборд", "url": reverse("frontend:dashboard")},
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_cashier_context(user, now, today):
    del now
    invoices = _scoped_invoices(user)
    payments = _scoped_payments(user)
    adjustments = _scoped_payment_adjustments(user)

    unpaid_statuses = [Invoice.InvoiceStatus.FORMED, Invoice.InvoiceStatus.POSTED]
    unpaid_qs = invoices.filter(status__in=unpaid_statuses)
    unpaid_total = unpaid_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    payments_today = payments.filter(paid_at__date=today)
    payments_today_total = payments_today.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    refunds_today = adjustments.filter(
        adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
        adjusted_at__date=today,
    )
    refunds_today_total = refunds_today.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    kpis = [
        {
            "label": "Счетов к оплате",
            "value": unpaid_qs.count(),
            "note": f"Сумма {unpaid_total}",
        },
        {
            "label": "Оплаты сегодня",
            "value": payments_today.count(),
            "note": f"Сумма {payments_today_total}",
        },
        {
            "label": "Возвраты сегодня",
            "value": refunds_today.count(),
            "note": f"Сумма {refunds_today_total}",
        },
        {
            "label": "Корректировки сегодня",
            "value": adjustments.filter(adjusted_at__date=today).count(),
            "note": "",
        },
    ]

    panels = [
        _panel(
            "Счета к оплате",
            [
                _row(
                    f"Счет #{invoice.id} · {invoice.visit.pet.name}",
                    f"{invoice.get_status_display()} · к оплате {invoice.total_amount}",
                )
                for invoice in unpaid_qs.order_by("-created_at")[:10]
            ],
        ),
        _panel(
            "Последние оплаты",
            [
                _row(
                    f"Платеж #{payment.id} · счет #{payment.invoice_id}",
                    (
                        f"{payment.amount} · {payment.get_method_display()} · "
                        f"{timezone.localtime(payment.paid_at).strftime('%d.%m %H:%M')}"
                    ),
                )
                for payment in payments.order_by("-paid_at")[:10]
            ],
        ),
        _panel(
            "Последние корректировки",
            [
                _row(
                    f"#{adjustment.id} · платеж #{adjustment.payment_id}",
                    (
                        f"{adjustment.get_adjustment_type_display()} · "
                        f"{adjustment.amount} · {adjustment.reason}"
                    ),
                )
                for adjustment in adjustments.order_by("-adjusted_at")[:10]
            ],
        ),
    ]

    quick_links = _clean_links(
        [
            _quick_link(user, "Финансы", "frontend:finance-board", "billing.view_invoice"),
            _quick_link(user, "Документы", "frontend:documents-board", "documents.view_generateddocument"),
            _quick_link(user, "Дашборд", "frontend:dashboard"),
        ]
    )
    return {"kpis": kpis, "panels": panels, "quick_links": quick_links}


def _build_role_context(role_key: str, user, now, today):
    builders = {
        "administrator": _build_admin_context,
        "registrar": _build_registrar_context,
        "veterinarian": _build_veterinarian_context,
        "assistant": _build_assistant_context,
        "lab_technician": _build_lab_context,
        "inventory_manager": _build_inventory_context,
        "cashier": _build_cashier_context,
    }
    builder = builders.get(role_key, _build_registrar_context)
    return builder(user, now, today)


@login_required
def role_home_redirect(request):
    return redirect("frontend:role-home-detail", role_key=_primary_role(request.user))


@login_required
def role_home_detail(request, role_key: str):
    if role_key not in ROLE_HOME_ORDER:
        raise PermissionDenied

    available_roles = _available_roles(request.user)
    if role_key not in available_roles:
        raise PermissionDenied

    now = timezone.now()
    today = timezone.localdate()
    role_meta = ROLE_HOME_META[role_key]
    role_context = _build_role_context(role_key, request.user, now, today)

    switch_roles = [
        {
            "key": role,
            "title": ROLE_HOME_META[role]["title"],
            "url": reverse("frontend:role-home-detail", kwargs={"role_key": role}),
            "active": role == role_key,
        }
        for role in available_roles
    ]

    return render(
        request,
        "frontend/role_home.html",
        {
            "role_key": role_key,
            "role_title": role_meta["title"],
            "role_subtitle": role_meta["subtitle"],
            "today": today,
            "switch_roles": switch_roles,
            **role_context,
        },
    )
