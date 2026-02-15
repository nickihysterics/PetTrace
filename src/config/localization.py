from __future__ import annotations

import sys

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin

ADMIN_BRANDING = {
    "site_header": "Администрирование PetTrace",
    "site_title": "Админ-панель PetTrace",
    "index_title": "Панель управления клиникой",
}

FIELD_LABELS = {
    "id": "ID",
    "public_id": "Публичный ID",
    "created_at": "Создано",
    "updated_at": "Обновлено",
    "code": "Код",
    "name": "Название",
    "description": "Описание",
    "status": "Статус",
    "is_active": "Активен",
    "owner": "Владелец",
    "pet": "Пациент",
    "visit": "Визит",
    "appointment": "Запись",
    "branch": "Филиал",
    "cabinet": "Кабинет",
    "room": "Кабинет/комната",
    "phone": "Телефон",
    "email": "Электронная почта",
    "address": "Адрес",
    "notes": "Заметки",
    "first_name": "Имя",
    "last_name": "Фамилия",
    "discount_percent": "Скидка, %",
    "is_blacklisted": "Черный список",
    "preferred_branch": "Предпочтительный филиал",
    "home_branch": "Домашний филиал",
    "allowed_branches": "Разрешенные филиалы",
    "allowed_cabinets": "Разрешенные кабинеты",
    "limit_to_assigned_cabinets": "Только назначенные кабинеты",
    "consent_type": "Тип согласия",
    "accepted_at": "Принято",
    "revoked_at": "Отозвано",
    "document_file": "Файл документа",
    "species": "Вид",
    "breed": "Порода",
    "sex": "Пол",
    "birth_date": "Дата рождения",
    "weight_kg": "Вес, кг",
    "allergies": "Аллергии",
    "vaccination_notes": "Вакцинации",
    "insurance_number": "Страховой номер",
    "microchip_id": "ID микрочипа",
    "qr_token": "QR-токен",
    "file": "Файл",
    "title": "Название",
    "veterinarian": "Врач",
    "assistant": "Ассистент",
    "service_type": "Тип услуги",
    "start_at": "Начало",
    "end_at": "Окончание",
    "duration_minutes": "Длительность, мин",
    "queue_number": "Номер очереди",
    "checked_in_at": "Отмечен в регистратуре",
    "completed_at": "Завершено",
    "created_by": "Создано пользователем",
    "scheduled_at": "Запланировано",
    "started_at": "Начато",
    "ended_at": "Завершено",
    "chief_complaint": "Жалобы",
    "anamnesis": "Анамнез",
    "physical_exam": "Осмотр",
    "diagnosis_summary": "Диагноз (кратко)",
    "recommendations": "Рекомендации",
    "from_status": "Из статуса",
    "to_status": "В статус",
    "actor": "Пользователь",
    "event_at": "Время события",
    "admitted_at": "Поступление",
    "discharged_at": "Выписка",
    "cage_number": "Номер клетки",
    "care_plan": "План ухода",
    "feeding_instructions": "Инструкции по кормлению",
    "is_primary": "Основной",
    "value": "Значение",
    "unit": "Единица",
    "medication_name": "Препарат",
    "dosage": "Дозировка",
    "frequency": "Кратность",
    "duration_days": "Длительность, дней",
    "route": "Путь введения",
    "warnings": "Предупреждения",
    "instructions": "Инструкции",
    "performed_by": "Выполнил",
    "performed_at": "Выполнено",
    "equipment_type": "Тип оборудования",
    "capacity": "Вместимость",
    "required_cabinet_type": "Требуемый тип кабинета",
    "default_duration_minutes": "Длительность по умолчанию, мин",
    "requirement": "Требование услуги",
    "quantity": "Количество",
    "ordered_by": "Назначил",
    "ordered_at": "Назначено",
    "sla_minutes": "SLA, мин",
    "specimen_type": "Тип образца",
    "turnaround_minutes": "Срок выполнения, мин",
    "collected_by": "Кто взял материал",
    "collected_at": "Время забора",
    "received_at": "Время приема",
    "in_process_at": "Передано в обработку",
    "done_at": "Готово",
    "collection_room": "Место забора",
    "rejection_reason": "Причина брака",
    "rejection_note": "Комментарий брака",
    "tube_type": "Тип пробирки",
    "lot_number": "Партия",
    "expires_at": "Годен до",
    "inventory_item": "Складская позиция",
    "tube": "Пробирка",
    "specimen": "Образец",
    "label_value": "Значение этикетки",
    "printed_at": "Напечатано",
    "location": "Локация",
    "lab_test": "Лабораторный тест",
    "parameter_name": "Параметр",
    "reference_range": "Референс",
    "flag": "Флаг",
    "comment": "Комментарий",
    "approved_by": "Утвердил",
    "approved_at": "Утверждено",
    "approval_note": "Примечание к утверждению",
    "sku": "Артикул",
    "category": "Категория",
    "min_stock": "Мин. остаток",
    "item": "Позиция",
    "quantity_received": "Поступило",
    "quantity_available": "Доступно",
    "supplier": "Поставщик",
    "batch": "Партия",
    "movement_type": "Тип движения",
    "reason": "Причина",
    "reference_type": "Тип ссылки",
    "reference_id": "ID ссылки",
    "moved_by": "Операцию выполнил",
    "amount": "Сумма",
    "currency": "Валюта",
    "invoice": "Счет",
    "method": "Способ оплаты",
    "paid_at": "Оплачено",
    "external_id": "Внешний ID",
    "price_item": "Прайс-позиция",
    "line_total": "Сумма строки",
    "invoice_line": "Строка счета",
    "subtotal_amount": "Подытог",
    "total_amount": "Итого",
    "issued_at": "Выставлен",
    "task_type": "Тип задачи",
    "priority": "Приоритет",
    "assigned_to": "Исполнитель",
    "due_at": "Срок",
    "lab_order": "Лабораторный заказ",
    "recipient": "Получатель",
    "channel": "Канал",
    "body": "Текст",
    "payload": "Данные",
    "sent_at": "Отправлено",
    "error_message": "Текст ошибки",
    "action": "Действие",
    "model_label": "Модель",
    "object_pk": "ID объекта",
    "changes": "Изменения",
    "ip_address": "IP-адрес",
    "user_agent": "User-Agent",
    "job_title": "Должность",
    "date_joined": "Дата регистрации",
    "last_login": "Последний вход",
    "is_staff": "Доступ в админку",
    "groups": "Группы",
    "is_superuser": "Суперпользователь",
    "user_permissions": "Права пользователя",
    "diagnosis_code": "Код диагноза",
    "diagnosis_title": "Название диагноза",
    "dose_mg_per_kg": "Доза мг/кг",
    "fixed_dose_mg": "Фиксированная доза, мг",
    "min_dose_mg": "Мин. доза, мг",
    "max_dose_mg": "Макс. доза, мг",
    "allergy_keyword": "Ключ аллергии",
    "severity": "Критичность",
    "resolved_at": "Разрешено",
    "resolved_by": "Разрешил",
    "procedure_order": "Назначенная процедура",
    "template": "Шаблон",
    "is_required": "Обязательный",
    "sort_order": "Порядок",
    "is_completed": "Выполнено",
    "reminder_type": "Тип напоминания",
    "direction": "Направление",
    "scheduled_for": "Запланировано на",
    "sent_by": "Отправил",
    "message": "Сообщение",
}

MODEL_VERBOSE_NAMES = {
    "users.User": ("пользователь", "пользователи"),
    "users.UserAccessProfile": ("профиль доступа", "профили доступа"),
    "owners.Owner": ("владелец", "владельцы"),
    "owners.ConsentDocument": ("согласие", "согласия"),
    "pets.Pet": ("животное", "животные"),
    "pets.PetAttachment": ("вложение животного", "вложения животных"),
    "facilities.Branch": ("филиал", "филиалы"),
    "facilities.Cabinet": ("кабинет", "кабинеты"),
    "facilities.EquipmentType": ("тип оборудования", "типы оборудования"),
    "facilities.Equipment": ("оборудование", "оборудование"),
    "facilities.ServiceRequirement": ("требование услуги", "требования услуг"),
    "facilities.ServiceRequirementEquipment": ("оборудование услуги", "оборудование услуг"),
    "crm.OwnerTag": ("тег владельца", "теги владельцев"),
    "crm.OwnerTagAssignment": ("привязка тега", "привязки тегов"),
    "crm.CommunicationLog": ("коммуникация", "коммуникации"),
    "crm.Reminder": ("напоминание", "напоминания"),
    "visits.Appointment": ("запись на прием", "записи на прием"),
    "visits.Visit": ("визит", "визиты"),
    "visits.VisitEvent": ("событие визита", "события визита"),
    "visits.Hospitalization": ("госпитализация", "госпитализации"),
    "visits.Diagnosis": ("диагноз", "диагнозы"),
    "visits.Observation": ("показатель осмотра", "показатели осмотра"),
    "visits.Prescription": ("назначение", "назначения"),
    "visits.ProcedureOrder": ("назначенная процедура", "назначенные процедуры"),
    "clinical.ClinicalProtocol": ("клинический протокол", "клинические протоколы"),
    "clinical.ProtocolMedicationTemplate": ("шаблон назначения", "шаблоны назначений"),
    "clinical.ProtocolProcedureTemplate": ("шаблон процедуры", "шаблоны процедур"),
    "clinical.ContraindicationRule": ("правило противопоказания", "правила противопоказаний"),
    "clinical.ClinicalAlert": ("клиническое предупреждение", "клинические предупреждения"),
    "clinical.ProcedureChecklistTemplate": ("шаблон чек-листа", "шаблоны чек-листов"),
    "clinical.ProcedureChecklistTemplateItem": (
        "пункт шаблона чек-листа",
        "пункты шаблонов чек-листа",
    ),
    "clinical.ProcedureChecklist": ("чек-лист процедуры", "чек-листы процедур"),
    "clinical.ProcedureChecklistItem": ("пункт чек-листа", "пункты чек-листа"),
    "labs.LabOrder": ("лабораторный заказ", "лабораторные заказы"),
    "labs.LabTest": ("лабораторный тест", "лабораторные тесты"),
    "labs.Specimen": ("образец", "образцы"),
    "labs.Tube": ("пробирка", "пробирки"),
    "labs.SpecimenTube": ("использование пробирки", "использование пробирок"),
    "labs.ContainerLabel": ("этикетка контейнера", "этикетки контейнеров"),
    "labs.SpecimenEvent": ("событие образца", "события образца"),
    "labs.LabResultValue": ("значение результата", "значения результатов"),
    "inventory.InventoryItem": ("складская позиция", "складские позиции"),
    "inventory.Batch": ("партия", "партии"),
    "inventory.StockMovement": ("движение склада", "движения склада"),
    "billing.PriceItem": ("прайс-позиция", "прайс-позиции"),
    "billing.Invoice": ("счет", "счета"),
    "billing.InvoiceLine": ("строка счета", "строки счета"),
    "billing.Payment": ("платеж", "платежи"),
    "tasks.Task": ("задача", "задачи"),
    "tasks.Notification": ("уведомление", "уведомления"),
    "audit.AuditLog": ("аудит-запись", "аудит-записи"),
}

CHOICE_LABELS = {
    "CONSULTATION": "Консультация",
    "PROCEDURE": "Процедурный",
    "LAB": "Лаборатория",
    "SURGERY": "Операционный",
    "INPATIENT": "Стационар",
    "OTHER": "Другое",
    "AVAILABLE": "Доступно",
    "IN_USE": "В работе",
    "MAINTENANCE": "Обслуживание",
    "OUT_OF_SERVICE": "Выведено из эксплуатации",
    "DRAFT": "Черновик",
    "ISSUED": "Выставлен",
    "PAID": "Оплачен",
    "CANCELED": "Отменен",
    "CASH": "Наличные",
    "CARD": "Карта",
    "TRANSFER": "Перевод",
    "SMS": "SMS",
    "EMAIL": "Эл. почта",
    "PHONE": "Телефон",
    "TELEGRAM": "Telegram",
    "IN_APP": "В системе",
    "OUTBOUND": "Исходящее",
    "INBOUND": "Входящее",
    "PENDING": "Ожидает",
    "SENT": "Отправлено",
    "FAILED": "Ошибка",
    "VACCINATION": "Вакцинация",
    "FOLLOW_UP": "Повторный прием",
    "CHECKUP": "Профосмотр",
    "DUE": "К сроку",
    "DISMISSED": "Отклонено",
    "OVERDUE": "Просрочено",
    "CREATE": "Создание",
    "UPDATE": "Изменение",
    "DELETE": "Удаление",
    "STATUS_CHANGE": "Смена статуса",
    "API_MUTATION": "Изменение через API",
    "SCHEDULED": "Запланирован",
    "WAITING": "Ожидает",
    "IN_PROGRESS": "В работе",
    "COMPLETED": "Завершен",
    "CLOSED": "Закрыт",
    "BOOKED": "Записан",
    "CHECKED_IN": "Отмечен",
    "IN_ROOM": "В кабинете",
    "NO_SHOW": "Не явился",
    "ADMITTED": "Госпитализирован",
    "UNDER_OBSERVATION": "Под наблюдением",
    "CRITICAL": "Критическое состояние",
    "DISCHARGED": "Выписан",
    "PLANNED": "Запланирован",
    "DONE": "Готово",
    "INFO": "Инфо",
    "WARNING": "Предупреждение",
    "BLOCKING": "Блокирующее",
    "TODO": "К выполнению",
    "COLLECT_SPECIMEN": "Забор образца",
    "LAB_RECEIVE": "Прием в лаборатории",
    "LOW": "Низкий",
    "MEDIUM": "Средний",
    "HIGH": "Высокий",
    "URGENT": "Срочный",
    "PERSONAL_DATA": "Персональные данные",
    "ANESTHESIA": "Анестезия",
    "GENERAL": "Общее согласие",
    "COLLECTED": "Собран",
    "IN_TRANSPORT": "В транспортировке",
    "RECEIVED": "Принят",
    "IN_PROCESS": "В обработке",
    "REJECTED": "Отклонен",
    "HEMOLYZED": "Гемолиз",
    "INSUFFICIENT_VOLUME": "Недостаточный объем",
    "CONTAMINATED": "Контаминирован",
    "EXPIRED": "Просрочен",
    "EDTA": "EDTA",
    "SERUM": "Сыворотка",
    "URINE": "Моча",
    "STOOL": "Кал",
    "NORMAL": "Норма",
    "DOG": "Собака",
    "CAT": "Кошка",
    "RABBIT": "Кролик",
    "BIRD": "Птица",
    "MALE": "Самец",
    "FEMALE": "Самка",
    "UNKNOWN": "Неизвестно",
    "ACTIVE": "Активен",
    "DECEASED": "Умер",
    "ARCHIVED": "Архив",
    "MEDICINE": "Препарат",
    "CONSUMABLE": "Расходник",
    "WRITE_OFF": "Списание",
    "ADJUSTMENT": "Корректировка",
    "RESERVATION": "Резерв",
    "RELEASE": "Снятие резерва",
}

FIELD_CHOICE_LABELS = {
    ("inventory.StockMovement", "movement_type", "INBOUND"): "Приход",
}

_is_patched = False
_original_formfield_for_dbfield = BaseModelAdmin.formfield_for_dbfield
_COMMANDS_WITHOUT_MODEL_PATCH = {
    "makemigrations",
    "migrate",
    "showmigrations",
    "sqlmigrate",
}


def _patch_admin_form_labels():
    def localized_formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = _original_formfield_for_dbfield(self, db_field, request, **kwargs)
        if formfield and db_field.name in FIELD_LABELS:
            formfield.label = FIELD_LABELS[db_field.name]
        return formfield

    BaseModelAdmin.formfield_for_dbfield = localized_formfield_for_dbfield


def _localize_model_verbose_names():
    for model_label, (verbose_name, verbose_name_plural) in MODEL_VERBOSE_NAMES.items():
        try:
            model = apps.get_model(model_label)
        except LookupError:
            continue
        model._meta.verbose_name = verbose_name
        model._meta.verbose_name_plural = verbose_name_plural


def _localize_field_verbose_names():
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if not hasattr(field, "name") or not hasattr(field, "verbose_name"):
                continue
            if field.name not in FIELD_LABELS:
                continue
            field.verbose_name = FIELD_LABELS[field.name]


def _localize_choice_labels():
    for model in apps.get_models():
        model_label = f"{model._meta.app_label}.{model.__name__}"
        for field in model._meta.get_fields():
            choices = getattr(field, "choices", None)
            if not choices:
                continue

            localized_choices = []
            changed = False
            for value, label in list(choices):
                if isinstance(label, (list, tuple)):
                    group_items = []
                    for group_value, group_label in label:
                        mapped_group_label = FIELD_CHOICE_LABELS.get(
                            (model_label, field.name, str(group_value)),
                            CHOICE_LABELS.get(str(group_value), group_label),
                        )
                        if mapped_group_label != group_label:
                            changed = True
                        group_items.append((group_value, mapped_group_label))
                    localized_choices.append((value, group_items))
                    continue

                mapped_label = FIELD_CHOICE_LABELS.get(
                    (model_label, field.name, str(value)),
                    CHOICE_LABELS.get(str(value), label),
                )
                if mapped_label != label:
                    changed = True
                localized_choices.append((value, mapped_label))

            if changed:
                field.choices = localized_choices


def apply_localization():
    global _is_patched
    if _is_patched:
        return

    admin.site.site_header = ADMIN_BRANDING["site_header"]
    admin.site.site_title = ADMIN_BRANDING["site_title"]
    admin.site.index_title = ADMIN_BRANDING["index_title"]

    if not _COMMANDS_WITHOUT_MODEL_PATCH.intersection(set(sys.argv)):
        _localize_model_verbose_names()
        _localize_field_verbose_names()
        _localize_choice_labels()
    _patch_admin_form_labels()

    _is_patched = True


apply_localization()
