from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.billing.models import (
    DiscountRule,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAdjustment,
    PriceItem,
)
from apps.common.services import get_setting_bool
from apps.documents.models import (
    ClinicalDocument,
    DocumentStoragePolicy,
    DocumentTemplate,
    GeneratedDocument,
)
from apps.documents.services import generate_document_from_template
from apps.facilities.models import HospitalBed
from apps.inventory.models import InventoryItem
from apps.inventory.services import write_off_inventory_item
from apps.labs.models import LabOrder
from apps.pets.models import Pet
from apps.users.access import (
    get_user_role_names,
    is_unrestricted_user,
    restrict_queryset_for_user_scope,
)
from apps.visits.models import (
    HospitalBedStay,
    Hospitalization,
    HospitalProcedurePlan,
    HospitalVitalRecord,
    MedicationAdministration,
    Prescription,
    Visit,
    VisitEvent,
)

MODULE_CATALOG = {
    "dashboard": {
        "title": "Операционный дашборд",
        "description": "KPI, очередь, активные визиты, открытые задачи.",
        "url_name": "frontend:dashboard",
        "perms": [],
    },
    "appointments": {
        "title": "Приемы и очередь",
        "description": "Запись на прием, check-in, запуск и завершение визитов.",
        "url_name": "frontend:appointments-board",
        "perms": ["visits.view_appointment"],
    },
    "labs": {
        "title": "Лаборатория",
        "description": "Статусы заказов и образцов, контроль результатов.",
        "url_name": "frontend:labs-board",
        "perms": ["labs.view_laborder"],
    },
    "documents": {
        "title": "Документы и медиа",
        "description": "Вложения по пациенту/визиту, версии файлов, генерация PDF по шаблонам.",
        "url_name": "frontend:documents-board",
        "perms": [
            "documents.view_clinicaldocument",
            "documents.view_generateddocument",
            "documents.view_documenttemplate",
        ],
    },
    "hospitalization": {
        "title": "Стационар",
        "description": "Госпитализация, койко-места, vitals, план процедур.",
        "url_name": "frontend:hospitalization-board",
        "perms": ["visits.view_hospitalization"],
    },
    "mar": {
        "title": "MAR",
        "description": (
            "Medication Administration Record: факт введения, пропуски, "
            "отмены, списания."
        ),
        "url_name": "frontend:mar-board",
        "perms": ["visits.view_medicationadministration"],
    },
    "finance": {
        "title": "Финансы",
        "description": "Счета, скидки, оплаты, возвраты/корректировки.",
        "url_name": "frontend:finance-board",
        "perms": ["billing.view_invoice"],
    },
}


ROLE_CABINET_CONFIG = {
    "administrator": {
        "title": "Администратор",
        "summary": "Полный доступ ко всем модулям и настройкам.",
        "modules": [
            "dashboard",
            "appointments",
            "labs",
            "documents",
            "hospitalization",
            "mar",
            "finance",
        ],
        "capabilities": [
            "Управляет пользователями, ролями, правами и системными настройками.",
            "Контролирует весь поток: регистратура, медицина, лаборатория, склад и финансы.",
            "Видит полный аудит изменений и эксплуатационные метрики.",
        ],
    },
    "registrar": {
        "title": "Регистратор",
        "summary": "Фронт-офис: CRM, запись, документы, координация стационара.",
        "modules": ["dashboard", "appointments", "documents", "hospitalization", "finance"],
        "capabilities": [
            "Создает владельцев/пациентов, ведет запись и очередь.",
            "Оформляет документы и вложения по пациенту/визиту.",
            "Видит счета для координации закрытия визита.",
        ],
    },
    "veterinarian": {
        "title": "Врач",
        "summary": "Клиническое ведение визита, стационар, назначения и контроль исполнения.",
        "modules": [
            "dashboard",
            "appointments",
            "labs",
            "documents",
            "hospitalization",
            "mar",
            "finance",
        ],
        "capabilities": [
            "Ведет прием, формирует назначения и клинические решения.",
            "Работает со стационаром: статусы, bed-management, vitals, план процедур.",
            "Контролирует MAR и итоговые финансовые документы визита.",
        ],
    },
    "assistant": {
        "title": "Ассистент/процедурная",
        "summary": "Исполнение процедур, заборов, госпитальных задач и MAR.",
        "modules": ["dashboard", "appointments", "labs", "documents", "hospitalization", "mar"],
        "capabilities": [
            "Отмечает выполнение процедур и этапов лабораторного контура.",
            "Ведет vitals и план процедур в стационаре.",
            "Фиксирует введения/пропуски/отмены лекарств в MAR.",
        ],
    },
    "lab_technician": {
        "title": "Лаборант",
        "summary": "Поток лаборатории и документы по результатам.",
        "modules": ["dashboard", "labs", "documents"],
        "capabilities": [
            "Переводит статусы заказов/образцов и ведет контроль SLA.",
            "Вносит и утверждает результаты анализов.",
            "Прикрепляет лабораторные файлы и генерируемые документы.",
        ],
    },
    "inventory_manager": {
        "title": "Склад/закупки",
        "summary": "Учет остатков и списаний, контроль расхода материалов.",
        "modules": ["dashboard", "mar"],
        "capabilities": [
            "Контролирует списания со склада по факту выполнения назначений.",
            "Анализирует расход препаратов и материалов.",
            "Следит за корректностью движения остатков.",
        ],
    },
    "cashier": {
        "title": "Кассир/бухгалтер",
        "summary": "Закрытие финансового контура визита.",
        "modules": ["dashboard", "documents", "finance"],
        "capabilities": [
            "Формирует и проводит счета, регистрирует оплаты.",
            "Применяет скидки и обрабатывает корректировки платежей.",
            "Готовит закрывающие документы по визиту.",
        ],
    },
}


def _has_any_perm(user, perms: list[str]) -> bool:
    if not perms:
        return True
    return any(user.has_perm(code) for code in perms)


def _ensure_perm(user, perm_code: str):
    if not user.has_perm(perm_code):
        raise PermissionDenied


def _ensure_any_perm(user, perms: list[str]):
    if not _has_any_perm(user, perms):
        raise PermissionDenied


def _redirect_with_query(view_name: str, **params):
    base_url = reverse(view_name)
    filtered = {key: value for key, value in params.items() if value not in ("", None)}
    if not filtered:
        return redirect(base_url)
    return redirect(f"{base_url}?{urlencode(filtered)}")


def _parse_decimal(
    raw_value: str | None, field_name: str, *, allow_blank: bool = True
) -> Decimal | None:
    if raw_value in (None, ""):
        if allow_blank:
            return None
        raise ValidationError(f"Поле '{field_name}' обязательно")
    try:
        return Decimal(str(raw_value).replace(",", "."))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"Поле '{field_name}' должно быть числом")


def _parse_int(raw_value: str | None, field_name: str, *, allow_blank: bool = True) -> int | None:
    if raw_value in (None, ""):
        if allow_blank:
            return None
        raise ValidationError(f"Поле '{field_name}' обязательно")
    try:
        return int(str(raw_value))
    except (TypeError, ValueError):
        raise ValidationError(f"Поле '{field_name}' должно быть целым числом")


def _parse_datetime(raw_value: str | None, field_name: str, *, allow_blank: bool = True):
    if raw_value in (None, ""):
        if allow_blank:
            return None
        raise ValidationError(f"Поле '{field_name}' обязательно")
    parsed = parse_datetime(str(raw_value))
    if parsed is None:
        raise ValidationError(f"Поле '{field_name}' имеет неверный формат даты/времени")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _module_payload(module_key: str) -> dict | None:
    module = MODULE_CATALOG.get(module_key)
    if not module:
        return None
    return {
        "key": module_key,
        "title": module["title"],
        "description": module["description"],
        "url": reverse(module["url_name"]),
    }


def _role_modules_for_user(user, role_key: str) -> list[dict]:
    role_cfg = ROLE_CABINET_CONFIG.get(role_key, {})
    module_items: list[dict] = []
    for module_key in role_cfg.get("modules", []):
        module = MODULE_CATALOG.get(module_key)
        if not module:
            continue
        if _has_any_perm(user, module["perms"]):
            payload = _module_payload(module_key)
            if payload:
                module_items.append(payload)
    return module_items


@login_required
def role_cabinets_index(request):
    user = request.user
    user_roles = set(get_user_role_names(user))
    available_roles: list[str]

    if is_unrestricted_user(user):
        available_roles = list(ROLE_CABINET_CONFIG.keys())
    else:
        available_roles = [role for role in ROLE_CABINET_CONFIG if role in user_roles]

    role_cards = []
    for role in available_roles:
        cfg = ROLE_CABINET_CONFIG[role]
        modules = _role_modules_for_user(user, role)
        if not modules and not is_unrestricted_user(user):
            continue
        role_cards.append(
            {
                "key": role,
                "title": cfg["title"],
                "summary": cfg["summary"],
                "capabilities": cfg["capabilities"],
                "modules": modules,
                "detail_url": reverse("frontend:role-cabinet-detail", kwargs={"role_key": role}),
            }
        )

    return render(
        request,
        "frontend/role_cabinets.html",
        {
            "role_cards": role_cards,
        },
    )


@login_required
def role_cabinet_detail(request, role_key: str):
    cfg = ROLE_CABINET_CONFIG.get(role_key)
    if not cfg:
        raise PermissionDenied

    if not is_unrestricted_user(request.user):
        user_roles = set(get_user_role_names(request.user))
        if role_key not in user_roles:
            raise PermissionDenied

    return render(
        request,
        "frontend/role_cabinet_detail.html",
        {
            "role_key": role_key,
            "role_title": cfg["title"],
            "role_summary": cfg["summary"],
            "role_capabilities": cfg["capabilities"],
            "modules": _role_modules_for_user(request.user, role_key),
        },
    )


def _scoped_clinical_documents(user):
    queryset = ClinicalDocument.objects.select_related(
        "pet",
        "visit",
        "visit__pet",
        "visit__owner",
        "lab_order",
        "lab_order__visit",
        "lab_order__visit__pet",
        "uploaded_by",
        "replaced_by",
        "storage_policy",
    )
    if is_unrestricted_user(user):
        return queryset

    visit_docs = restrict_queryset_for_user_scope(
        queryset=queryset.filter(visit__isnull=False),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
        allow_unassigned=True,
    )
    lab_docs = restrict_queryset_for_user_scope(
        queryset=queryset.filter(lab_order__isnull=False),
        user=user,
        branch_field="lab_order__visit__branch",
        cabinet_field="lab_order__visit__cabinet",
        allow_unassigned=True,
    )
    pet_docs = queryset.filter(visit__isnull=True, lab_order__isnull=True)
    return queryset.filter(
        Q(id__in=visit_docs.values("id"))
        | Q(id__in=lab_docs.values("id"))
        | Q(id__in=pet_docs.values("id"))
    ).distinct()


def _scoped_generated_documents(user):
    queryset = GeneratedDocument.objects.select_related(
        "template",
        "visit",
        "visit__pet",
        "visit__owner",
        "owner",
        "pet",
        "lab_order",
        "lab_order__visit",
        "generated_by",
    )
    if is_unrestricted_user(user):
        return queryset

    visit_docs = restrict_queryset_for_user_scope(
        queryset=queryset.filter(visit__isnull=False),
        user=user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
        allow_unassigned=True,
    )
    lab_docs = restrict_queryset_for_user_scope(
        queryset=queryset.filter(lab_order__isnull=False),
        user=user,
        branch_field="lab_order__visit__branch",
        cabinet_field="lab_order__visit__cabinet",
        allow_unassigned=True,
    )
    detached_docs = queryset.filter(visit__isnull=True, lab_order__isnull=True)
    return queryset.filter(
        Q(id__in=visit_docs.values("id"))
        | Q(id__in=lab_docs.values("id"))
        | Q(id__in=detached_docs.values("id"))
    ).distinct()


@login_required
def documents_board(request):
    _ensure_any_perm(
        request.user,
        [
            "documents.view_clinicaldocument",
            "documents.view_generateddocument",
            "documents.view_documenttemplate",
        ],
    )

    scoped_visits_qs = restrict_queryset_for_user_scope(
        queryset=Visit.objects.select_related("pet", "owner", "branch", "cabinet"),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )
    scoped_orders_qs = restrict_queryset_for_user_scope(
        queryset=LabOrder.objects.select_related("visit", "visit__pet", "visit__owner"),
        user=request.user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )
    scoped_docs_qs = _scoped_clinical_documents(request.user)
    scoped_generated_qs = _scoped_generated_documents(request.user)

    query = (request.GET.get("q") or request.POST.get("q") or "").strip()

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "upload_document":
                _ensure_perm(request.user, "documents.add_clinicaldocument")
                uploaded_file = request.FILES.get("file")
                if uploaded_file is None:
                    raise ValidationError("Файл не выбран")

                target_kind = (request.POST.get("target_kind") or "").strip()
                target_visit = None
                target_pet = None
                target_lab_order = None
                if target_kind == "visit":
                    target_visit = get_object_or_404(
                        scoped_visits_qs, pk=request.POST.get("visit_id")
                    )
                elif target_kind == "pet":
                    _ensure_perm(request.user, "pets.view_pet")
                    target_pet = get_object_or_404(
                        Pet.objects.select_related("owner"), pk=request.POST.get("pet_id")
                    )
                elif target_kind == "lab_order":
                    target_lab_order = get_object_or_404(
                        scoped_orders_qs, pk=request.POST.get("lab_order_id")
                    )
                else:
                    raise ValidationError("Укажите сущность для привязки документа")

                storage_policy = None
                storage_policy_id = request.POST.get("storage_policy_id")
                if storage_policy_id:
                    storage_policy = get_object_or_404(
                        DocumentStoragePolicy.objects.filter(is_active=True),
                        pk=storage_policy_id,
                    )
                    max_size_bytes = storage_policy.max_file_size_mb * 1024 * 1024
                    if getattr(uploaded_file, "size", 0) > max_size_bytes:
                        limit_mb = storage_policy.max_file_size_mb
                        raise ValidationError(
                            f"Файл превышает лимит политики хранения: {limit_mb} MB"
                        )

                document = ClinicalDocument(
                    document_type=request.POST.get("document_type")
                    or ClinicalDocument.DocumentType.OTHER,
                    title=(request.POST.get("title") or "").strip(),
                    description=(request.POST.get("description") or "").strip(),
                    file=uploaded_file,
                    mime_type=(
                        request.POST.get("mime_type") or getattr(uploaded_file, "content_type", "")
                    ).strip(),
                    file_size_bytes=getattr(uploaded_file, "size", 0),
                    storage_policy=storage_policy,
                    pet=target_pet,
                    visit=target_visit,
                    lab_order=target_lab_order,
                    uploaded_by=request.user if request.user.is_authenticated else None,
                )
                document.full_clean()
                document.save()
                messages.success(request, f"Документ #{document.id} загружен.")

            elif action == "replace_document":
                _ensure_perm(request.user, "documents.change_clinicaldocument")
                current_doc = get_object_or_404(
                    scoped_docs_qs.filter(is_current=True),
                    pk=request.POST.get("document_id"),
                )
                replacement_file = request.FILES.get("file")
                if replacement_file is None:
                    raise ValidationError("Для версии документа нужен новый файл")

                replacement = ClinicalDocument(
                    document_type=current_doc.document_type,
                    title=(request.POST.get("title") or current_doc.title).strip(),
                    description=(
                        request.POST.get("description") or current_doc.description
                    ).strip(),
                    file=replacement_file,
                    mime_type=(
                        request.POST.get("mime_type")
                        or getattr(replacement_file, "content_type", "")
                        or current_doc.mime_type
                    ).strip(),
                    file_size_bytes=getattr(replacement_file, "size", 0),
                    storage_policy=current_doc.storage_policy,
                    pet=current_doc.pet,
                    visit=current_doc.visit,
                    lab_order=current_doc.lab_order,
                    uploaded_by=request.user if request.user.is_authenticated else None,
                )
                current_doc.replace_with(
                    new_document=replacement,
                    actor=request.user if request.user.is_authenticated else None,
                )
                replacement.full_clean()
                replacement.save()
                messages.success(request, f"Создана новая версия документа #{replacement.id}.")

            elif action == "generate_document":
                _ensure_perm(request.user, "documents.view_documenttemplate")
                template = get_object_or_404(
                    DocumentTemplate.objects.filter(is_active=True),
                    pk=request.POST.get("template_id"),
                )
                visit = None
                owner = None
                pet = None
                lab_order = None

                if request.POST.get("visit_id"):
                    visit = get_object_or_404(scoped_visits_qs, pk=request.POST.get("visit_id"))
                    owner = visit.owner
                    pet = visit.pet

                if request.POST.get("lab_order_id"):
                    lab_order = get_object_or_404(
                        scoped_orders_qs, pk=request.POST.get("lab_order_id")
                    )
                    if visit is None:
                        visit = lab_order.visit
                        owner = visit.owner
                        pet = visit.pet

                payload_raw = (request.POST.get("payload_json") or "").strip()
                payload_data = json.loads(payload_raw) if payload_raw else {}
                if not isinstance(payload_data, dict):
                    raise ValidationError("payload_json должен быть JSON-объектом")

                generated = generate_document_from_template(
                    template=template,
                    payload=payload_data,
                    filename_prefix=template.code.lower(),
                    generated_by=request.user if request.user.is_authenticated else None,
                    visit=visit,
                    owner=owner,
                    pet=pet,
                    lab_order=lab_order,
                )
                messages.success(request, f"Документ #{generated.id} сформирован.")
            else:
                messages.error(request, "Неизвестное действие")
        except (ValidationError, json.JSONDecodeError) as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:documents-board", q=query)

    if query:
        scoped_docs_qs = scoped_docs_qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(document_type__icontains=query)
            | Q(pet__name__icontains=query)
            | Q(visit__pet__name__icontains=query)
            | Q(lab_order__visit__pet__name__icontains=query)
        )
        scoped_generated_qs = scoped_generated_qs.filter(
            Q(template__name__icontains=query)
            | Q(template__code__icontains=query)
            | Q(pet__name__icontains=query)
            | Q(visit__pet__name__icontains=query)
            | Q(lab_order__visit__pet__name__icontains=query)
        )

    return render(
        request,
        "frontend/documents_board.html",
        {
            "query": query,
            "documents": list(scoped_docs_qs.order_by("-created_at")[:80]),
            "generated_documents": list(scoped_generated_qs.order_by("-generated_at")[:80]),
            "can_upload_document": request.user.has_perm("documents.add_clinicaldocument"),
            "can_replace_document": request.user.has_perm("documents.change_clinicaldocument"),
            "can_generate_document": request.user.has_perm("documents.view_documenttemplate"),
            "document_types": list(ClinicalDocument.DocumentType.choices),
            "templates": list(
                DocumentTemplate.objects.filter(is_active=True).order_by("name")[:80]
            ),
            "storage_policies": list(
                DocumentStoragePolicy.objects.filter(is_active=True).order_by("name")
            ),
            "recent_visits": list(scoped_visits_qs.order_by("-created_at")[:60]),
            "recent_lab_orders": list(scoped_orders_qs.order_by("-ordered_at")[:60]),
            "pets_for_docs": list(Pet.objects.select_related("owner").order_by("-created_at")[:60])
            if request.user.has_perm("pets.view_pet")
            else [],
        },
    )


def _close_current_bed_stay(hospitalization: Hospitalization, actor=None, notes: str = "") -> None:
    current_stay = (
        hospitalization.bed_stays.filter(is_current=True).order_by("-moved_in_at").first()
    )
    if current_stay is None:
        return
    current_stay.is_current = False
    current_stay.moved_out_at = timezone.now()
    if notes:
        current_stay.notes = notes
    if actor and current_stay.moved_by_id is None:
        current_stay.moved_by = actor
    current_stay.save(
        update_fields=["is_current", "moved_out_at", "notes", "moved_by", "updated_at"]
    )


def _assign_hospitalization_bed(
    hospitalization: Hospitalization, bed: HospitalBed, actor=None, notes: str = ""
):
    if bed.ward.branch_id != hospitalization.branch_id:
        raise ValidationError("Койко-место не относится к филиалу госпитализации")
    if not bed.is_active:
        raise ValidationError("Койко-место неактивно")
    if bed.status not in {HospitalBed.BedStatus.AVAILABLE, HospitalBed.BedStatus.OCCUPIED}:
        raise ValidationError(f"Койко-место нельзя назначить в статусе {bed.status}")
    is_occupied_by_other = (
        Hospitalization.objects.filter(current_bed=bed).exclude(id=hospitalization.id).exists()
    )
    if is_occupied_by_other:
        raise ValidationError("Койко-место уже занято")

    previous_bed = hospitalization.current_bed
    if previous_bed and previous_bed.id == bed.id:
        return hospitalization

    if previous_bed and previous_bed.status == HospitalBed.BedStatus.OCCUPIED:
        previous_bed.status = HospitalBed.BedStatus.AVAILABLE
        previous_bed.save(update_fields=["status", "updated_at"])
        _close_current_bed_stay(
            hospitalization,
            actor=actor,
            notes=f"Перемещение из {previous_bed.code}. {notes}".strip(),
        )

    bed.status = HospitalBed.BedStatus.OCCUPIED
    bed.save(update_fields=["status", "updated_at"])

    hospitalization.current_bed = bed
    if hospitalization.cabinet_id is None and bed.cabinet_id:
        hospitalization.cabinet = bed.cabinet
    hospitalization.save(update_fields=["current_bed", "cabinet", "updated_at"])

    HospitalBedStay.objects.create(
        hospitalization=hospitalization,
        bed=bed,
        moved_by=actor if actor and actor.is_authenticated else None,
        notes=notes,
    )
    return hospitalization


def _release_hospitalization_bed(
    hospitalization: Hospitalization,
    *,
    actor=None,
    notes: str = "",
    to_status: str = HospitalBed.BedStatus.AVAILABLE,
):
    bed = hospitalization.current_bed
    if bed is None:
        return
    _close_current_bed_stay(hospitalization, actor=actor, notes=notes)
    if bed.status == HospitalBed.BedStatus.OCCUPIED:
        bed.status = to_status
        bed.save(update_fields=["status", "updated_at"])
    hospitalization.current_bed = None
    hospitalization.save(update_fields=["current_bed", "updated_at"])


@login_required
def hospitalization_board(request):
    _ensure_perm(request.user, "visits.view_hospitalization")

    status_filter = (request.GET.get("status") or request.POST.get("status_filter") or "").strip()
    scoped_hospitalizations_qs = restrict_queryset_for_user_scope(
        queryset=Hospitalization.objects.select_related(
            "visit",
            "visit__pet",
            "visit__owner",
            "branch",
            "cabinet",
            "current_bed",
            "current_bed__ward",
            "current_bed__cabinet",
        ).prefetch_related(
            Prefetch(
                "vitals",
                queryset=HospitalVitalRecord.objects.select_related("recorded_by").order_by(
                    "-measured_at"
                ),
            ),
            Prefetch(
                "procedure_plans",
                queryset=HospitalProcedurePlan.objects.select_related("completed_by").order_by(
                    "scheduled_at"
                ),
            ),
            Prefetch(
                "bed_stays",
                queryset=HospitalBedStay.objects.select_related("bed", "moved_by").order_by(
                    "-moved_in_at"
                ),
            ),
        ),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )
    scoped_visits_qs = restrict_queryset_for_user_scope(
        queryset=Visit.objects.select_related("pet", "owner", "branch", "cabinet"),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )
    scoped_beds_qs = restrict_queryset_for_user_scope(
        queryset=HospitalBed.objects.select_related("ward", "ward__branch", "cabinet"),
        user=request.user,
        branch_field="ward__branch",
        cabinet_field="cabinet",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create_hospitalization":
                _ensure_perm(request.user, "visits.add_hospitalization")
                visit = get_object_or_404(scoped_visits_qs, pk=request.POST.get("visit_id"))
                if Hospitalization.objects.filter(visit=visit).exists():
                    raise ValidationError("Для визита уже существует госпитализация")
                if visit.branch_id is None:
                    raise ValidationError("У визита не указан филиал")
                hospitalization = Hospitalization.objects.create(
                    visit=visit,
                    branch=visit.branch,
                    cabinet=visit.cabinet,
                    cage_number=(request.POST.get("cage_number") or "").strip(),
                    care_plan=(request.POST.get("care_plan") or "").strip(),
                    feeding_instructions=(request.POST.get("feeding_instructions") or "").strip(),
                )
                bed_id = request.POST.get("bed_id")
                if bed_id:
                    bed = get_object_or_404(
                        scoped_beds_qs.filter(ward__branch=visit.branch), pk=bed_id
                    )
                    _assign_hospitalization_bed(
                        hospitalization,
                        bed,
                        actor=request.user,
                        notes="Первичное назначение койко-места",
                    )
                messages.success(request, f"Госпитализация #{hospitalization.id} создана.")

            elif action == "transition_hospitalization":
                _ensure_perm(request.user, "visits.change_hospitalization")
                hospitalization = get_object_or_404(
                    scoped_hospitalizations_qs, pk=request.POST.get("hospitalization_id")
                )
                new_status = (request.POST.get("new_status") or "").strip()
                if not new_status:
                    raise ValidationError("Не указан новый статус")
                hospitalization.transition_to(new_status)
                if new_status in {
                    Hospitalization.HospitalizationStatus.DISCHARGED,
                    Hospitalization.HospitalizationStatus.CANCELED,
                }:
                    _release_hospitalization_bed(
                        hospitalization,
                        actor=request.user,
                        notes=f"Завершение госпитализации со статусом {new_status}",
                        to_status=HospitalBed.BedStatus.CLEANING,
                    )
                hospitalization.save(update_fields=["status", "discharged_at", "updated_at"])
                messages.success(request, f"Статус госпитализации #{hospitalization.id} обновлен.")

            elif action == "assign_bed":
                _ensure_perm(request.user, "visits.change_hospitalization")
                hospitalization = get_object_or_404(
                    scoped_hospitalizations_qs, pk=request.POST.get("hospitalization_id")
                )
                bed = get_object_or_404(
                    scoped_beds_qs.filter(ward__branch=hospitalization.branch, is_active=True),
                    pk=request.POST.get("bed_id"),
                )
                _assign_hospitalization_bed(
                    hospitalization,
                    bed,
                    actor=request.user,
                    notes=(request.POST.get("notes") or "").strip(),
                )
                messages.success(
                    request,
                    f"Для госпитализации #{hospitalization.id} назначено койко-место {bed.code}.",
                )

            elif action == "release_bed":
                _ensure_perm(request.user, "visits.change_hospitalization")
                hospitalization = get_object_or_404(
                    scoped_hospitalizations_qs, pk=request.POST.get("hospitalization_id")
                )
                _release_hospitalization_bed(
                    hospitalization,
                    actor=request.user,
                    notes=(request.POST.get("notes") or "").strip(),
                    to_status=HospitalBed.BedStatus.AVAILABLE,
                )
                messages.success(
                    request, f"Койко-место освобождено для госпитализации #{hospitalization.id}."
                )

            elif action == "add_vital":
                _ensure_perm(request.user, "visits.add_hospitalvitalrecord")
                hospitalization = get_object_or_404(
                    scoped_hospitalizations_qs, pk=request.POST.get("hospitalization_id")
                )
                vital = HospitalVitalRecord(
                    hospitalization=hospitalization,
                    measured_at=_parse_datetime(request.POST.get("measured_at"), "measured_at")
                    or timezone.now(),
                    temperature_c=_parse_decimal(
                        request.POST.get("temperature_c"), "temperature_c"
                    ),
                    pulse_bpm=_parse_int(request.POST.get("pulse_bpm"), "pulse_bpm"),
                    respiratory_rate=_parse_int(
                        request.POST.get("respiratory_rate"), "respiratory_rate"
                    ),
                    appetite_status=(
                        request.POST.get("appetite_status")
                        or HospitalVitalRecord.AppetiteStatus.NORMAL
                    ),
                    water_intake_ml=_parse_decimal(
                        request.POST.get("water_intake_ml"), "water_intake_ml"
                    ),
                    urine_output_ml=_parse_decimal(
                        request.POST.get("urine_output_ml"), "urine_output_ml"
                    ),
                    notes=(request.POST.get("notes") or "").strip(),
                    recorded_by=request.user if request.user.is_authenticated else None,
                )
                vital.full_clean()
                vital.save()
                messages.success(
                    request, f"Vitals добавлены для госпитализации #{hospitalization.id}."
                )

            elif action == "add_plan":
                _ensure_perm(request.user, "visits.add_hospitalprocedureplan")
                hospitalization = get_object_or_404(
                    scoped_hospitalizations_qs, pk=request.POST.get("hospitalization_id")
                )
                plan = HospitalProcedurePlan(
                    hospitalization=hospitalization,
                    title=(request.POST.get("title") or "").strip(),
                    instructions=(request.POST.get("instructions") or "").strip(),
                    scheduled_at=_parse_datetime(
                        request.POST.get("scheduled_at"), "scheduled_at", allow_blank=False
                    ),
                )
                plan.full_clean()
                plan.save()
                messages.success(request, f"План процедуры #{plan.id} добавлен.")

            elif action == "update_plan":
                _ensure_perm(request.user, "visits.change_hospitalprocedureplan")
                plan = get_object_or_404(
                    HospitalProcedurePlan.objects.select_related("hospitalization"),
                    pk=request.POST.get("plan_id"),
                )
                if not scoped_hospitalizations_qs.filter(id=plan.hospitalization_id).exists():
                    raise PermissionDenied
                new_status = (request.POST.get("new_status") or "").strip()
                allowed_status = {code for code, _label in HospitalProcedurePlan.PlanStatus.choices}
                if new_status not in allowed_status:
                    raise ValidationError("Недопустимый статус плана")
                plan.status = new_status
                plan.notes = (request.POST.get("notes") or plan.notes).strip()
                if new_status == HospitalProcedurePlan.PlanStatus.DONE:
                    if plan.completed_at is None:
                        plan.completed_at = timezone.now()
                    if plan.completed_by_id is None and request.user.is_authenticated:
                        plan.completed_by = request.user
                plan.save(
                    update_fields=["status", "notes", "completed_at", "completed_by", "updated_at"]
                )
                messages.success(request, f"План процедуры #{plan.id} обновлен.")
            else:
                messages.error(request, "Неизвестное действие")
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:hospitalization-board", status=status_filter)

    hospitalization_status_labels = dict(Hospitalization.HospitalizationStatus.choices)
    queryset = scoped_hospitalizations_qs.order_by("-admitted_at")
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    hospitalizations = list(queryset[:40])
    for hospitalization in hospitalizations:
        hospitalization.allowed_transitions = [
            {"code": code, "label": hospitalization_status_labels.get(code, code)}
            for code in sorted(
                hospitalization.ALLOWED_TRANSITIONS.get(hospitalization.status, set())
            )
        ]
        hospitalization.recent_vitals = list(hospitalization.vitals.all()[:5])
        hospitalization.recent_plans = list(hospitalization.procedure_plans.all()[:8])
        hospitalization.current_stay = next(
            (stay for stay in hospitalization.bed_stays.all() if stay.is_current),
            None,
        )

    return render(
        request,
        "frontend/hospitalization_board.html",
        {
            "hospitalizations": hospitalizations,
            "status_filter": status_filter,
            "status_choices": list(Hospitalization.HospitalizationStatus.choices),
            "appetite_choices": list(HospitalVitalRecord.AppetiteStatus.choices),
            "plan_status_choices": list(HospitalProcedurePlan.PlanStatus.choices),
            "admission_candidates": list(
                scoped_visits_qs.filter(hospitalization__isnull=True)
                .exclude(status__in=[Visit.VisitStatus.CANCELED, Visit.VisitStatus.CLOSED])
                .order_by("-created_at")[:80]
            ),
            "beds": list(
                scoped_beds_qs.filter(is_active=True).order_by(
                    "ward__branch__name", "ward__code", "code"
                )[:200]
            ),
            "can_create_hospitalization": request.user.has_perm("visits.add_hospitalization"),
            "can_change_hospitalization": request.user.has_perm("visits.change_hospitalization"),
            "can_add_vitals": request.user.has_perm("visits.add_hospitalvitalrecord"),
            "can_add_plan": request.user.has_perm("visits.add_hospitalprocedureplan"),
            "can_change_plan": request.user.has_perm("visits.change_hospitalprocedureplan"),
        },
    )


@login_required
def mar_board(request):
    _ensure_perm(request.user, "visits.view_medicationadministration")
    can_view_inventory_items = request.user.has_perm("inventory.view_inventoryitem")

    status_filter = (request.GET.get("status") or request.POST.get("status_filter") or "").strip()
    scoped_prescriptions_qs = restrict_queryset_for_user_scope(
        queryset=Prescription.objects.select_related("visit", "visit__pet", "visit__owner"),
        user=request.user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )
    scoped_administrations_qs = restrict_queryset_for_user_scope(
        queryset=MedicationAdministration.objects.select_related(
            "prescription",
            "prescription__visit",
            "prescription__visit__pet",
            "prescription__visit__owner",
            "given_by",
            "inventory_item",
            "batch",
        ),
        user=request.user,
        branch_field="prescription__visit__branch",
        cabinet_field="prescription__visit__cabinet",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create_administration":
                _ensure_perm(request.user, "visits.add_medicationadministration")
                prescription = get_object_or_404(
                    scoped_prescriptions_qs, pk=request.POST.get("prescription_id")
                )
                administration = MedicationAdministration(
                    prescription=prescription,
                    scheduled_at=_parse_datetime(request.POST.get("scheduled_at"), "scheduled_at")
                    or timezone.now(),
                    dose_amount=_parse_decimal(request.POST.get("dose_amount"), "dose_amount"),
                    dose_unit=(request.POST.get("dose_unit") or "").strip(),
                    route=(request.POST.get("route") or "").strip(),
                    deviation_note=(request.POST.get("deviation_note") or "").strip(),
                )
                inventory_item_id = request.POST.get("inventory_item_id")
                if inventory_item_id:
                    if not can_view_inventory_items:
                        raise PermissionDenied
                    administration.inventory_item = get_object_or_404(
                        InventoryItem.objects.filter(is_active=True),
                        pk=inventory_item_id,
                    )
                administration.full_clean()
                administration.save()
                messages.success(request, f"Запись MAR #{administration.id} создана.")

            elif action == "mark_given":
                _ensure_perm(request.user, "visits.change_medicationadministration")
                administration = get_object_or_404(
                    scoped_administrations_qs, pk=request.POST.get("administration_id")
                )
                if administration.status != MedicationAdministration.AdministrationStatus.PLANNED:
                    raise ValidationError(
                        f"Нельзя отметить как введено в статусе {administration.status}"
                    )

                inventory_item_id = request.POST.get("inventory_item_id")
                if inventory_item_id:
                    if not can_view_inventory_items:
                        raise PermissionDenied
                    administration.inventory_item = get_object_or_404(
                        InventoryItem.objects.filter(is_active=True),
                        pk=inventory_item_id,
                    )

                quantity_written_off = _parse_decimal(
                    request.POST.get("quantity_written_off"),
                    "quantity_written_off",
                )
                if quantity_written_off is not None and quantity_written_off < 0:
                    raise ValidationError("quantity_written_off не может быть отрицательным")

                if (
                    administration.inventory_item
                    and quantity_written_off
                    and quantity_written_off > 0
                ):
                    movements = write_off_inventory_item(
                        item=administration.inventory_item,
                        quantity=quantity_written_off,
                        reason=f"Medication administration #{administration.id}",
                        moved_by=request.user if request.user.is_authenticated else None,
                        reference_type="MedicationAdministration",
                        reference_id=str(administration.id),
                    )
                    administration.quantity_written_off = sum(
                        (movement.quantity for movement in movements),
                        Decimal("0"),
                    )
                    administration.write_off_note = (
                        request.POST.get("write_off_note") or administration.write_off_note
                    ).strip()
                elif quantity_written_off is not None:
                    administration.quantity_written_off = quantity_written_off

                dose_amount = _parse_decimal(request.POST.get("dose_amount"), "dose_amount")
                if dose_amount is not None:
                    administration.dose_amount = dose_amount
                if request.POST.get("dose_unit") not in (None, ""):
                    administration.dose_unit = request.POST.get("dose_unit", "").strip()
                if request.POST.get("route") not in (None, ""):
                    administration.route = request.POST.get("route", "").strip()
                if request.POST.get("deviation_note") not in (None, ""):
                    administration.deviation_note = request.POST.get("deviation_note", "").strip()

                administration.status = MedicationAdministration.AdministrationStatus.GIVEN
                administration.given_at = timezone.now()
                administration.given_by = request.user if request.user.is_authenticated else None
                administration.save()
                messages.success(request, f"MAR #{administration.id} отмечен как введенный.")

            elif action == "mark_skipped":
                _ensure_perm(request.user, "visits.change_medicationadministration")
                administration = get_object_or_404(
                    scoped_administrations_qs, pk=request.POST.get("administration_id")
                )
                if administration.status == MedicationAdministration.AdministrationStatus.GIVEN:
                    raise ValidationError("Нельзя пропустить уже введенное назначение")
                administration.status = MedicationAdministration.AdministrationStatus.SKIPPED
                administration.deviation_note = (
                    request.POST.get("reason") or administration.deviation_note
                ).strip()
                administration.save(update_fields=["status", "deviation_note", "updated_at"])
                messages.success(request, f"MAR #{administration.id} отмечен как пропущенный.")

            elif action == "mark_canceled":
                _ensure_perm(request.user, "visits.change_medicationadministration")
                administration = get_object_or_404(
                    scoped_administrations_qs, pk=request.POST.get("administration_id")
                )
                if administration.status == MedicationAdministration.AdministrationStatus.GIVEN:
                    raise ValidationError("Нельзя отменить уже введенное назначение")
                administration.status = MedicationAdministration.AdministrationStatus.CANCELED
                administration.deviation_note = (
                    request.POST.get("reason") or administration.deviation_note
                ).strip()
                administration.save(update_fields=["status", "deviation_note", "updated_at"])
                messages.success(request, f"MAR #{administration.id} отменен.")
            else:
                messages.error(request, "Неизвестное действие")
        except ValidationError as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:mar-board", status=status_filter)

    status_labels = dict(MedicationAdministration.AdministrationStatus.choices)
    queryset = scoped_administrations_qs.order_by("scheduled_at", "created_at")
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    administrations = list(queryset[:120])

    counts = {
        code: scoped_administrations_qs.filter(status=code).count()
        for code, _label in MedicationAdministration.AdministrationStatus.choices
    }
    status_cards = [
        {"code": code, "label": label, "count": counts.get(code, 0)}
        for code, label in MedicationAdministration.AdministrationStatus.choices
    ]

    return render(
        request,
        "frontend/mar_board.html",
        {
            "administrations": administrations,
            "status_filter": status_filter,
            "status_choices": list(MedicationAdministration.AdministrationStatus.choices),
            "status_labels": status_labels,
            "status_counts": counts,
            "status_cards": status_cards,
            "prescriptions": list(scoped_prescriptions_qs.order_by("-created_at")[:120]),
            "inventory_items": (
                list(InventoryItem.objects.filter(is_active=True).order_by("name")[:120])
                if can_view_inventory_items
                else []
            ),
            "can_create": request.user.has_perm("visits.add_medicationadministration"),
            "can_change": request.user.has_perm("visits.change_medicationadministration"),
        },
    )


def _sum_payments(invoice: Invoice) -> Decimal:
    return Payment.objects.filter(invoice=invoice).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")


def _sum_adjustments(invoice: Invoice) -> tuple[Decimal, Decimal]:
    refunds = PaymentAdjustment.objects.filter(
        payment__invoice=invoice,
        adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    corrections = PaymentAdjustment.objects.filter(
        payment__invoice=invoice,
        adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return refunds, corrections


def _sync_invoice_payment_status(*, invoice: Invoice, actor=None) -> Invoice:
    paid_total = _sum_payments(invoice)
    refunds, corrections = _sum_adjustments(invoice)
    net_paid = paid_total - abs(refunds) + corrections

    if net_paid >= invoice.total_amount and invoice.total_amount > 0:
        if invoice.status != Invoice.InvoiceStatus.PAID:
            invoice.status = Invoice.InvoiceStatus.PAID
            invoice.save(update_fields=["status", "updated_at"])

            visit = invoice.visit
            auto_close_visit = get_setting_bool("visit.auto_close_on_payment", default=True)
            if auto_close_visit and visit.status == Visit.VisitStatus.COMPLETED:
                previous = visit.status
                visit.transition_to(Visit.VisitStatus.CLOSED)
                visit.save(update_fields=["status", "ended_at", "updated_at"])
                VisitEvent.objects.create(
                    visit=visit,
                    from_status=previous,
                    to_status=visit.status,
                    actor=actor,
                    notes=f"Визит автоматически закрыт после оплаты счета #{invoice.id}",
                )
        return invoice

    if invoice.status == Invoice.InvoiceStatus.PAID:
        invoice.status = Invoice.InvoiceStatus.POSTED
        invoice.save(update_fields=["status", "updated_at"])
    return invoice


def _resolve_discount_rule(invoice: Invoice, *, promo_code: str = "", rule_id: int | None = None):
    if rule_id:
        return DiscountRule.objects.filter(id=rule_id, is_active=True).first()

    visit_owner = getattr(invoice.visit, "owner", None)
    if promo_code:
        return DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.PROMO,
            promo_code__iexact=promo_code,
        ).first()

    owner_rule = None
    if visit_owner:
        owner_rule = DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.OWNER,
            owner=visit_owner,
            auto_apply=True,
        ).first()
    if owner_rule:
        return owner_rule

    if visit_owner:
        owner_tag_ids = visit_owner.tag_assignments.values_list("tag_id", flat=True)
        tag_rule = DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.RuleScope.OWNER_TAG,
            owner_tag_id__in=owner_tag_ids,
            auto_apply=True,
        ).first()
        if tag_rule:
            return tag_rule

    return DiscountRule.objects.filter(
        is_active=True,
        scope=DiscountRule.RuleScope.GLOBAL,
        auto_apply=True,
    ).first()


@login_required
def finance_board(request):
    _ensure_perm(request.user, "billing.view_invoice")

    status_filter = (request.GET.get("status") or request.POST.get("status_filter") or "").strip()
    scoped_visits_qs = restrict_queryset_for_user_scope(
        queryset=Visit.objects.select_related("pet", "owner", "branch", "cabinet"),
        user=request.user,
        branch_field="branch",
        cabinet_field="cabinet",
    )
    scoped_invoices_qs = restrict_queryset_for_user_scope(
        queryset=Invoice.objects.select_related(
            "visit",
            "visit__pet",
            "visit__owner",
            "applied_discount_rule",
        ).prefetch_related(
            "lines",
            Prefetch(
                "payments",
                queryset=Payment.objects.prefetch_related("adjustments").order_by("-paid_at"),
            ),
        ),
        user=request.user,
        branch_field="visit__branch",
        cabinet_field="visit__cabinet",
    )

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create_invoice":
                _ensure_perm(request.user, "billing.add_invoice")
                visit = get_object_or_404(scoped_visits_qs, pk=request.POST.get("visit_id"))
                invoice, created = Invoice.objects.get_or_create(visit=visit)
                if created:
                    messages.success(request, f"Счет #{invoice.id} создан.")
                else:
                    messages.info(request, f"Счет #{invoice.id} уже существует.")

            elif action == "add_line":
                _ensure_perm(request.user, "billing.add_invoiceline")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                description = (request.POST.get("description") or "").strip()
                if not description:
                    raise ValidationError("Описание услуги обязательно")
                quantity = _parse_decimal(
                    request.POST.get("quantity"), "quantity", allow_blank=False
                )
                unit_price = _parse_decimal(
                    request.POST.get("unit_price"), "unit_price", allow_blank=False
                )
                if quantity <= 0 or unit_price < 0:
                    raise ValidationError("quantity должен быть > 0, unit_price должен быть >= 0")
                price_item = None
                if request.POST.get("price_item_id"):
                    price_item = get_object_or_404(
                        PriceItem.objects.filter(is_active=True),
                        pk=request.POST.get("price_item_id"),
                    )
                InvoiceLine.objects.create(
                    invoice=invoice,
                    price_item=price_item,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                )
                invoice.recalculate_totals()
                invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
                messages.success(request, f"Позиция добавлена в счет #{invoice.id}.")

            elif action == "void_line":
                _ensure_perm(request.user, "billing.change_invoiceline")
                line = get_object_or_404(
                    InvoiceLine.objects.select_related("invoice"),
                    pk=request.POST.get("line_id"),
                    invoice__in=scoped_invoices_qs,
                )
                line.is_void = True
                line.void_reason = (request.POST.get("void_reason") or "").strip()
                line.save(update_fields=["is_void", "void_reason", "updated_at"])
                invoice = line.invoice
                invoice.recalculate_totals()
                invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
                messages.success(request, f"Позиция #{line.id} сторнирована.")

            elif action == "invoice_recalculate":
                _ensure_perm(request.user, "billing.change_invoice")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                invoice.recalculate_totals()
                invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
                messages.success(request, f"Счет #{invoice.id} пересчитан.")

            elif action == "invoice_form":
                _ensure_perm(request.user, "billing.change_invoice")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                invoice.recalculate_totals()
                if invoice.status == Invoice.InvoiceStatus.DRAFT:
                    invoice.status = Invoice.InvoiceStatus.FORMED
                if invoice.formed_at is None:
                    invoice.formed_at = timezone.now()
                invoice.save(
                    update_fields=[
                        "subtotal_amount",
                        "total_amount",
                        "status",
                        "formed_at",
                        "updated_at",
                    ]
                )
                messages.success(request, f"Счет #{invoice.id} сформирован.")

            elif action == "invoice_post":
                _ensure_perm(request.user, "billing.change_invoice")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                invoice.recalculate_totals()
                if invoice.status == Invoice.InvoiceStatus.DRAFT:
                    invoice.status = Invoice.InvoiceStatus.FORMED
                invoice.status = Invoice.InvoiceStatus.POSTED
                if invoice.formed_at is None:
                    invoice.formed_at = timezone.now()
                if invoice.posted_at is None:
                    invoice.posted_at = timezone.now()
                invoice.save(
                    update_fields=[
                        "subtotal_amount",
                        "total_amount",
                        "status",
                        "formed_at",
                        "posted_at",
                        "updated_at",
                    ]
                )
                messages.success(request, f"Счет #{invoice.id} проведен.")

            elif action == "invoice_apply_discount":
                _ensure_perm(request.user, "billing.change_invoice")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                promo_code = (request.POST.get("promo_code") or "").strip()
                rule_raw = (request.POST.get("discount_rule_id") or "").strip()
                rule_id = int(rule_raw) if rule_raw else None
                rule = _resolve_discount_rule(invoice, promo_code=promo_code, rule_id=rule_id)
                invoice.recalculate_totals()
                if rule is None:
                    invoice.applied_discount_rule = None
                    invoice.discount_amount = Decimal("0")
                    invoice.discount_code = promo_code
                else:
                    invoice.applied_discount_rule = rule
                    invoice.discount_amount = rule.calculate_discount_amount(
                        invoice.subtotal_amount
                    )
                    invoice.discount_code = promo_code or rule.promo_code
                invoice.recalculate_totals()
                invoice.save(
                    update_fields=[
                        "applied_discount_rule",
                        "discount_amount",
                        "discount_code",
                        "subtotal_amount",
                        "total_amount",
                        "updated_at",
                    ]
                )
                messages.success(request, f"Скидка обновлена для счета #{invoice.id}.")

            elif action == "invoice_pay":
                _ensure_perm(request.user, "billing.add_payment")
                invoice = get_object_or_404(scoped_invoices_qs, pk=request.POST.get("invoice_id"))
                if invoice.status not in {
                    Invoice.InvoiceStatus.FORMED,
                    Invoice.InvoiceStatus.POSTED,
                    Invoice.InvoiceStatus.PAID,
                }:
                    raise ValidationError("Счет должен быть в статусе FORMED/POSTED/PAID")
                amount = _parse_decimal(request.POST.get("amount"), "amount", allow_blank=False)
                if amount <= 0:
                    raise ValidationError("amount должен быть положительным")
                method = (request.POST.get("method") or "").strip()
                allowed_methods = {code for code, _label in Payment.PaymentMethod.choices}
                if method not in allowed_methods:
                    raise ValidationError("Некорректный метод оплаты")
                payment = Payment.objects.create(
                    invoice=invoice,
                    method=method,
                    amount=amount,
                    external_id=(request.POST.get("external_id") or "").strip(),
                )
                _sync_invoice_payment_status(
                    invoice=invoice,
                    actor=request.user if request.user.is_authenticated else None,
                )
                messages.success(request, f"Платеж #{payment.id} добавлен в счет #{invoice.id}.")

            elif action == "payment_adjust":
                _ensure_perm(request.user, "billing.change_payment")
                payment = get_object_or_404(
                    Payment.objects.select_related("invoice"),
                    pk=request.POST.get("payment_id"),
                    invoice__in=scoped_invoices_qs,
                )
                adjustment_type = (request.POST.get("adjustment_type") or "").strip()
                allowed_types = {code for code, _label in PaymentAdjustment.AdjustmentType.choices}
                if adjustment_type not in allowed_types:
                    raise ValidationError("Некорректный тип корректировки")
                amount = _parse_decimal(request.POST.get("amount"), "amount", allow_blank=False)
                if amount <= 0:
                    raise ValidationError("amount должен быть положительным")
                reason = (request.POST.get("reason") or "").strip()
                if not reason:
                    raise ValidationError("Укажите причину корректировки")
                adjustment = PaymentAdjustment.objects.create(
                    payment=payment,
                    adjustment_type=adjustment_type,
                    amount=amount,
                    reason=reason,
                    adjusted_by=request.user if request.user.is_authenticated else None,
                    external_reference=(request.POST.get("external_reference") or "").strip(),
                )
                _sync_invoice_payment_status(
                    invoice=payment.invoice,
                    actor=request.user if request.user.is_authenticated else None,
                )
                messages.success(request, f"Корректировка #{adjustment.id} добавлена.")
            else:
                messages.error(request, "Неизвестное действие")
        except (ValidationError, ValueError) as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, detail)
        return _redirect_with_query("frontend:finance-board", status=status_filter)

    queryset = scoped_invoices_qs.order_by("-created_at")
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    invoices = list(queryset[:60])

    for invoice in invoices:
        paid_total = sum((payment.amount for payment in invoice.payments.all()), Decimal("0"))
        refunds = Decimal("0")
        corrections = Decimal("0")
        for payment in invoice.payments.all():
            for adjustment in payment.adjustments.all():
                if adjustment.adjustment_type == PaymentAdjustment.AdjustmentType.REFUND:
                    refunds += adjustment.amount
                else:
                    corrections += adjustment.amount
        invoice.ui_paid_total = paid_total
        invoice.ui_refunds_total = refunds
        invoice.ui_corrections_total = corrections
        invoice.ui_net_paid = paid_total - abs(refunds) + corrections
        invoice.ui_due_amount = max(invoice.total_amount - invoice.ui_net_paid, Decimal("0"))

    return render(
        request,
        "frontend/finance_board.html",
        {
            "status_filter": status_filter,
            "status_choices": list(Invoice.InvoiceStatus.choices),
            "invoices": invoices,
            "visits_without_invoice": list(
                scoped_visits_qs.filter(invoice__isnull=True)
                .exclude(status=Visit.VisitStatus.CANCELED)
                .order_by("-created_at")[:120]
            ),
            "price_items": list(PriceItem.objects.filter(is_active=True).order_by("name")[:200]),
            "discount_rules": list(
                DiscountRule.objects.filter(is_active=True).order_by("name")[:120]
            ),
            "payment_methods": list(Payment.PaymentMethod.choices),
            "adjustment_types": list(PaymentAdjustment.AdjustmentType.choices),
            "can_create_invoice": request.user.has_perm("billing.add_invoice"),
            "can_change_invoice": request.user.has_perm("billing.change_invoice"),
            "can_add_line": request.user.has_perm("billing.add_invoiceline"),
            "can_change_line": request.user.has_perm("billing.change_invoiceline"),
            "can_add_payment": request.user.has_perm("billing.add_payment"),
            "can_adjust_payment": request.user.has_perm("billing.change_payment"),
        },
    )
