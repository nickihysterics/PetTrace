from __future__ import annotations

from collections import Counter

from django.core.exceptions import ValidationError

from .models import Equipment, Service, ServiceRequirement, ServiceRequirementEquipment


def get_service_requirement(service_type: str = "", service: Service | None = None) -> ServiceRequirement | None:
    if service is not None:
        requirement = ServiceRequirement.objects.filter(service=service, is_active=True).first()
        if requirement is not None:
            return requirement

    if service_type:
        return ServiceRequirement.objects.filter(service_type=service_type, is_active=True).first()
    return None


def validate_appointment_resources(
    *,
    appointment_model,
    branch,
    cabinet,
    service_type: str,
    service: Service | None = None,
    start_at,
    end_at,
    ignore_appointment_id=None,
) -> ServiceRequirement | None:
    requirement = get_service_requirement(service_type, service=service)

    if cabinet is None:
        if requirement and requirement.required_cabinet_type:
            raise ValidationError(
                f"Услуга '{requirement.display_service_type}' требует кабинет типа {requirement.required_cabinet_type}"
            )
        return requirement

    if not cabinet.is_active:
        raise ValidationError("Выбранный кабинет неактивен")

    if branch and cabinet.branch_id != branch.id:
        raise ValidationError("Кабинет не принадлежит выбранному филиалу")

    overlap_qs = appointment_model.objects.filter(
        cabinet=cabinet,
        status__in=[
            appointment_model.AppointmentStatus.BOOKED,
            appointment_model.AppointmentStatus.CHECKED_IN,
            appointment_model.AppointmentStatus.IN_ROOM,
        ],
        start_at__lt=end_at,
        end_at__gt=start_at,
    )
    if ignore_appointment_id:
        overlap_qs = overlap_qs.exclude(id=ignore_appointment_id)
    if overlap_qs.exists():
        raise ValidationError(f"Кабинет {cabinet.code} занят в выбранный интервал времени")

    if requirement and requirement.required_cabinet_type:
        if cabinet.cabinet_type != requirement.required_cabinet_type:
            raise ValidationError(
                f"Услуга '{requirement.display_service_type}' требует кабинет типа {requirement.required_cabinet_type}"
            )

    if requirement:
        effective_branch = branch or cabinet.branch
        overlap_qs = appointment_model.objects.filter(
            branch=effective_branch,
            status__in=[
                appointment_model.AppointmentStatus.BOOKED,
                appointment_model.AppointmentStatus.CHECKED_IN,
                appointment_model.AppointmentStatus.IN_ROOM,
            ],
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        if ignore_appointment_id:
            overlap_qs = overlap_qs.exclude(id=ignore_appointment_id)

        overlapping_service_types = [
            service_type_value
            for service_type_value in overlap_qs.values_list("service_type", flat=True)
            if service_type_value
        ]
        overlapping_service_types.extend(
            [
                service_code
                for service_code in overlap_qs.exclude(service__isnull=True).values_list("service__code", flat=True)
                if service_code
            ]
        )
        service_counter = Counter(overlapping_service_types)

        for req in requirement.required_equipment.select_related("equipment_type"):
            available_count = Equipment.objects.filter(
                branch=effective_branch,
                equipment_type=req.equipment_type,
                status=Equipment.EquipmentStatus.AVAILABLE,
                is_active=True,
            ).count()
            reserved_quantity = 0
            if service_counter:
                equipment_requirements = ServiceRequirementEquipment.objects.filter(
                    requirement__is_active=True,
                    requirement__service_type__in=service_counter.keys(),
                    equipment_type=req.equipment_type,
                ).select_related("requirement")
                reserved_quantity = sum(
                    requirement_equipment.quantity * service_counter[requirement_equipment.requirement.service_type]
                    for requirement_equipment in equipment_requirements
                )
                service_equipment_requirements = ServiceRequirementEquipment.objects.filter(
                    requirement__is_active=True,
                    requirement__service__code__in=service_counter.keys(),
                    equipment_type=req.equipment_type,
                ).select_related("requirement", "requirement__service")
                reserved_quantity += sum(
                    requirement_equipment.quantity
                    * service_counter.get(requirement_equipment.requirement.service.code, 0)
                    for requirement_equipment in service_equipment_requirements
                    if requirement_equipment.requirement.service_id
                )

            available_for_window = max(available_count - reserved_quantity, 0)
            if available_for_window < req.quantity:
                raise ValidationError(
                    f"Недостаточно доступного оборудования типа {req.equipment_type.code} "
                    f"в филиале {effective_branch.code} на выбранный интервал"
                )

    return requirement
