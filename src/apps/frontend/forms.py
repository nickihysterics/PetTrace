from __future__ import annotations

from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.facilities.models import Branch, Cabinet
from apps.facilities.services import get_service_requirement, validate_appointment_resources
from apps.owners.models import Owner
from apps.pets.models import Pet
from apps.users.access import (
    ensure_user_can_access_branch_cabinet,
    restrict_queryset_for_user_scope,
)
from apps.visits.models import Appointment, Diagnosis, Prescription, ProcedureOrder, Visit


class StyledFormMixin:
    def _apply_widget_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check"
                continue
            if isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-textarea"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-input"
            if field.required:
                widget.attrs.setdefault("required", "required")


class FrontendAuthenticationForm(AuthenticationForm, StyledFormMixin):
    username = forms.EmailField(label="Эл. почта")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()


class OwnerForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Owner
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "preferred_branch",
            "discount_percent",
            "is_blacklisted",
            "address",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "phone": "Телефон",
            "email": "Эл. почта",
            "preferred_branch": "Предпочтительный филиал",
            "discount_percent": "Скидка, %",
            "is_blacklisted": "Черный список",
            "address": "Адрес",
            "notes": "Заметки",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_branch"].queryset = (
            Branch.objects.filter(is_active=True).order_by("name")
        )
        self._apply_widget_classes()


class PetForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Pet
        fields = [
            "owner",
            "name",
            "species",
            "breed",
            "sex",
            "birth_date",
            "weight_kg",
            "microchip_id",
            "status",
            "allergies",
            "vaccination_notes",
            "insurance_number",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "allergies": forms.Textarea(attrs={"rows": 3}),
            "vaccination_notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "owner": "Владелец",
            "name": "Кличка",
            "species": "Вид",
            "breed": "Порода",
            "sex": "Пол",
            "birth_date": "Дата рождения",
            "weight_kg": "Вес, кг",
            "microchip_id": "ID микрочипа",
            "status": "Статус",
            "allergies": "Аллергии",
            "vaccination_notes": "Вакцинации",
            "insurance_number": "Страховой номер",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = Owner.objects.order_by("last_name", "first_name")
        self._apply_widget_classes()


class AppointmentCreateForm(forms.ModelForm, StyledFormMixin):
    start_at = forms.DateTimeField(
        label="Начало",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Appointment
        fields = [
            "owner",
            "pet",
            "veterinarian",
            "service_type",
            "branch",
            "cabinet",
            "start_at",
            "duration_minutes",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "owner": "Владелец",
            "pet": "Животное",
            "veterinarian": "Врач",
            "service_type": "Услуга",
            "branch": "Филиал",
            "cabinet": "Кабинет",
            "duration_minutes": "Длительность, мин",
            "notes": "Комментарий",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["owner"].required = False
        self.fields["owner"].queryset = Owner.objects.order_by("last_name", "first_name")
        self.fields["pet"].queryset = Pet.objects.select_related("owner").order_by("name")
        branch_queryset = Branch.objects.filter(is_active=True).order_by("name")
        cabinet_queryset = Cabinet.objects.filter(is_active=True).select_related("branch")

        if self.user and self.user.is_authenticated:
            branch_queryset = restrict_queryset_for_user_scope(
                queryset=branch_queryset,
                user=self.user,
                branch_field="id",
                allow_unassigned=False,
            )
            cabinet_queryset = restrict_queryset_for_user_scope(
                queryset=cabinet_queryset,
                user=self.user,
                branch_field="branch",
                cabinet_field="id",
                allow_unassigned=False,
            )

        self.fields["branch"].queryset = branch_queryset
        self.fields["cabinet"].queryset = cabinet_queryset
        self.fields["veterinarian"].queryset = user_model.objects.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "email",
        )
        self._apply_widget_classes()

        if self.instance.pk and self.instance.start_at:
            local_dt = timezone.localtime(self.instance.start_at)
            self.initial["start_at"] = local_dt.strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned = super().clean()
        pet = cleaned.get("pet")
        owner = cleaned.get("owner")
        branch = cleaned.get("branch")
        cabinet = cleaned.get("cabinet")
        service_type = (cleaned.get("service_type") or "").strip()
        start_at = cleaned.get("start_at")
        duration = cleaned.get("duration_minutes") or 30

        if owner is None and pet is not None:
            owner = pet.owner
            cleaned["owner"] = owner

        if owner is None:
            raise forms.ValidationError("Укажите владельца или выберите животное с владельцем.")

        if pet is not None and owner is not None and pet.owner_id != owner.id:
            raise forms.ValidationError("Выбранный питомец не принадлежит указанному владельцу.")

        if branch is None and cabinet is not None:
            branch = cabinet.branch
            cleaned["branch"] = branch

        if branch and cabinet and cabinet.branch_id != branch.id:
            raise forms.ValidationError("Кабинет не принадлежит выбранному филиалу.")

        if self.user and self.user.is_authenticated:
            try:
                ensure_user_can_access_branch_cabinet(
                    user=self.user,
                    branch=branch,
                    cabinet=cabinet,
                )
            except DjangoValidationError as exc:
                message = exc.messages[0] if hasattr(exc, "messages") else str(exc)
                raise forms.ValidationError(message) from exc

        if duration <= 0:
            raise forms.ValidationError("Длительность приема должна быть больше 0.")

        duration_key = self.add_prefix("duration_minutes")
        requirement = get_service_requirement(service_type)
        if requirement and not self.data.get(duration_key):
            duration = requirement.default_duration_minutes
            cleaned["duration_minutes"] = duration

        if start_at is None:
            raise forms.ValidationError("Укажите время начала приема.")

        end_at = start_at + timedelta(minutes=duration)
        room = cabinet.code if cabinet else ""

        try:
            validate_appointment_resources(
                appointment_model=Appointment,
                branch=branch,
                cabinet=cabinet,
                service_type=service_type,
                start_at=start_at,
                end_at=end_at,
                ignore_appointment_id=self.instance.id if self.instance.pk else None,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            raise forms.ValidationError(message) from exc

        cleaned["end_at"] = end_at
        cleaned["room"] = room
        return cleaned

    def save(self, commit=True, user=None):
        appointment = super().save(commit=False)
        appointment.owner = self.cleaned_data["owner"]
        appointment.branch = self.cleaned_data["branch"]
        appointment.end_at = self.cleaned_data["end_at"]
        appointment.duration_minutes = self.cleaned_data["duration_minutes"]
        appointment.room = self.cleaned_data["room"]
        if user and user.is_authenticated and appointment.created_by_id is None:
            appointment.created_by = user
        if commit:
            appointment.save()
            self.save_m2m()
        return appointment


class VisitUpdateForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Visit
        fields = [
            "veterinarian",
            "assistant",
            "chief_complaint",
            "anamnesis",
            "physical_exam",
            "diagnosis_summary",
            "recommendations",
        ]
        widgets = {
            "chief_complaint": forms.Textarea(attrs={"rows": 2}),
            "anamnesis": forms.Textarea(attrs={"rows": 3}),
            "physical_exam": forms.Textarea(attrs={"rows": 4}),
            "diagnosis_summary": forms.Textarea(attrs={"rows": 3}),
            "recommendations": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "veterinarian": "Врач",
            "assistant": "Ассистент",
            "chief_complaint": "Жалобы",
            "anamnesis": "Анамнез",
            "physical_exam": "Осмотр",
            "diagnosis_summary": "Диагноз",
            "recommendations": "Рекомендации",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        users_qs = user_model.objects.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "email",
        )
        self.fields["veterinarian"].queryset = users_qs
        self.fields["assistant"].queryset = users_qs
        self._apply_widget_classes()


class DiagnosisCreateForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Diagnosis
        fields = ["code", "title", "description", "is_primary"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}
        labels = {
            "code": "Код",
            "title": "Диагноз",
            "description": "Описание",
            "is_primary": "Основной",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()


class PrescriptionCreateForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Prescription
        fields = ["medication_name", "dosage", "frequency", "duration_days", "route", "warnings"]
        widgets = {"warnings": forms.Textarea(attrs={"rows": 2})}
        labels = {
            "medication_name": "Препарат",
            "dosage": "Дозировка",
            "frequency": "Кратность",
            "duration_days": "Курс (дней)",
            "route": "Путь введения",
            "warnings": "Предупреждения",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()


class ProcedureCreateForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = ProcedureOrder
        fields = ["name", "instructions"]
        widgets = {"instructions": forms.Textarea(attrs={"rows": 2})}
        labels = {
            "name": "Процедура",
            "instructions": "Инструкция",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()
