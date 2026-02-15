from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.facilities.models import (
    Branch,
    Cabinet,
    HospitalBed,
    HospitalWard,
    Organization,
    Service,
    ServiceRequirement,
)

DEFAULT_CABINETS = [
    ("REG-01", "Регистратура", Cabinet.CabinetType.OTHER, 2),
    ("CONS-01", "Терапевтический кабинет 1", Cabinet.CabinetType.CONSULTATION, 1),
    ("CONS-02", "Терапевтический кабинет 2", Cabinet.CabinetType.CONSULTATION, 1),
    ("PROC-01", "Процедурный кабинет", Cabinet.CabinetType.PROCEDURE, 1),
    ("LAB-01", "Лаборатория", Cabinet.CabinetType.LAB, 2),
    ("SURG-01", "Операционная", Cabinet.CabinetType.SURGERY, 1),
    ("INPT-01", "Стационар", Cabinet.CabinetType.INPATIENT, 8),
    ("CASH-01", "Касса", Cabinet.CabinetType.OTHER, 1),
]

DEFAULT_SERVICE_REQUIREMENTS = [
    ("CONSULT", "Консультация", Service.ServiceCategory.CONSULTATION, Cabinet.CabinetType.CONSULTATION, 30),
    ("PROCEDURE", "Процедура", Service.ServiceCategory.PROCEDURE, Cabinet.CabinetType.PROCEDURE, 30),
    ("LAB_BASIC", "Лабораторная диагностика", Service.ServiceCategory.LAB, Cabinet.CabinetType.LAB, 20),
    ("SURGERY", "Операция", Service.ServiceCategory.SURGERY, Cabinet.CabinetType.SURGERY, 120),
    ("HOSPITAL", "Стационарное наблюдение", Service.ServiceCategory.HOSPITAL, Cabinet.CabinetType.INPATIENT, 60),
]


class Command(BaseCommand):
    help = "Создает базовую структуру филиала и кабинетов для ролей клиники"

    def add_arguments(self, parser):
        parser.add_argument("--branch-code", default="MAIN", help="Код филиала")
        parser.add_argument("--branch-name", default="Главный филиал", help="Название филиала")
        parser.add_argument("--organization-code", default="DEFAULT", help="Код организации")
        parser.add_argument("--organization-name", default="Основная клиника", help="Название организации")

    @transaction.atomic
    def handle(self, *args, **options):
        branch_code = options["branch_code"]
        branch_name = options["branch_name"]
        organization_code = options["organization_code"]
        organization_name = options["organization_name"]

        organization, _ = Organization.objects.get_or_create(
            code=organization_code,
            defaults={"name": organization_name, "is_active": True},
        )

        branch, branch_created = Branch.objects.get_or_create(
            code=branch_code,
            defaults={
                "name": branch_name,
                "organization": organization,
                "is_active": True,
            },
        )
        if branch_created:
            self.stdout.write(self.style.SUCCESS(f"Создан филиал: {branch.code} ({branch.name})"))
        else:
            update_fields = []
            if branch.name != branch_name:
                branch.name = branch_name
                update_fields.append("name")
            if branch.organization_id != organization.id:
                branch.organization = organization
                update_fields.append("organization")
            if update_fields:
                branch.save(update_fields=update_fields + ["updated_at"])
            self.stdout.write(self.style.WARNING(f"Филиал уже существовал: {branch.code}"))

        for code, name, cabinet_type, capacity in DEFAULT_CABINETS:
            cabinet, created = Cabinet.objects.get_or_create(
                branch=branch,
                code=code,
                defaults={
                    "name": name,
                    "cabinet_type": cabinet_type,
                    "capacity": capacity,
                    "is_active": True,
                },
            )
            if not created:
                update_fields = []
                if cabinet.name != name:
                    cabinet.name = name
                    update_fields.append("name")
                if cabinet.cabinet_type != cabinet_type:
                    cabinet.cabinet_type = cabinet_type
                    update_fields.append("cabinet_type")
                if cabinet.capacity != capacity:
                    cabinet.capacity = capacity
                    update_fields.append("capacity")
                if not cabinet.is_active:
                    cabinet.is_active = True
                    update_fields.append("is_active")
                if update_fields:
                    cabinet.save(update_fields=update_fields + ["updated_at"])
                    self.stdout.write(f"Обновлен кабинет: {branch.code}:{code}")
                else:
                    self.stdout.write(f"Кабинет уже настроен: {branch.code}:{code}")
                continue

            self.stdout.write(self.style.SUCCESS(f"Создан кабинет: {branch.code}:{code} ({name})"))

        for service_code, service_name, service_category, cabinet_type, default_duration in DEFAULT_SERVICE_REQUIREMENTS:
            service, _ = Service.objects.update_or_create(
                code=service_code,
                defaults={
                    "name": service_name,
                    "category": service_category,
                    "default_duration_minutes": default_duration,
                    "is_active": True,
                },
            )
            requirement, created = ServiceRequirement.objects.get_or_create(
                service=service,
                defaults={
                    "service_type": service_name,
                    "required_cabinet_type": cabinet_type,
                    "default_duration_minutes": default_duration,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Создано требование услуги: {service_code} -> {cabinet_type}"
                    )
                )
                continue

            update_fields = []
            if requirement.service_type != service_name:
                requirement.service_type = service_name
                update_fields.append("service_type")
            if requirement.required_cabinet_type != cabinet_type:
                requirement.required_cabinet_type = cabinet_type
                update_fields.append("required_cabinet_type")
            if requirement.default_duration_minutes != default_duration:
                requirement.default_duration_minutes = default_duration
                update_fields.append("default_duration_minutes")
            if not requirement.is_active:
                requirement.is_active = True
                update_fields.append("is_active")
            if update_fields:
                requirement.save(update_fields=update_fields + ["updated_at"])
                self.stdout.write(f"Обновлено требование услуги: {service_code}")
            else:
                self.stdout.write(f"Требование услуги уже настроено: {service_code}")

        ward, _ = HospitalWard.objects.get_or_create(
            branch=branch,
            code="WARD-01",
            defaults={"name": "Стационарная палата 1", "is_active": True},
        )
        for bed_code in ["B-01", "B-02", "B-03", "B-04"]:
            HospitalBed.objects.get_or_create(
                ward=ward,
                code=bed_code,
                defaults={"status": HospitalBed.BedStatus.AVAILABLE, "is_active": True},
            )

        self.stdout.write(self.style.SUCCESS("Базовая структура кабинетов развернута"))
