from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.tasks.models import Task
from apps.visits.models import Diagnosis, Prescription, ProcedureOrder

from .models import (
    ClinicalAlert,
    ClinicalProtocol,
    ContraindicationRule,
    ProcedureChecklist,
    ProcedureChecklistItem,
    ProcedureChecklistTemplate,
    ProtocolMedicationTemplate,
)


def calculate_recommended_dose_mg(*, weight_kg: Decimal | None, medication_template: ProtocolMedicationTemplate) -> Decimal:
    if medication_template.fixed_dose_mg is not None:
        dose = medication_template.fixed_dose_mg
    elif medication_template.dose_mg_per_kg is not None and weight_kg is not None:
        dose = medication_template.dose_mg_per_kg * weight_kg
    else:
        dose = Decimal("0")

    if medication_template.min_dose_mg is not None:
        dose = max(dose, medication_template.min_dose_mg)
    if medication_template.max_dose_mg is not None:
        dose = min(dose, medication_template.max_dose_mg)
    return dose.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def evaluate_prescription_contraindications(prescription: Prescription) -> list[ClinicalAlert]:
    pet = prescription.visit.pet
    allergies = (pet.allergies or "").lower()

    rules = ContraindicationRule.objects.filter(
        is_active=True,
        medication_name__iexact=prescription.medication_name,
    )
    rules = rules.filter(species__in=["", pet.species])

    ClinicalAlert.objects.filter(
        prescription=prescription,
        rule__isnull=False,
    ).delete()

    alerts: list[ClinicalAlert] = []
    blocking_messages: list[str] = []
    for rule in rules:
        if rule.allergy_keyword and rule.allergy_keyword.lower() not in allergies:
            continue

        message = rule.message or f"Contraindication detected for {prescription.medication_name}"
        alert = ClinicalAlert.objects.create(
            visit=prescription.visit,
            prescription=prescription,
            rule=rule,
            severity=rule.severity,
            message=message,
        )
        alerts.append(alert)
        if rule.severity == ContraindicationRule.Severity.BLOCKING:
            blocking_messages.append(message)

    if blocking_messages:
        combined = "; ".join(blocking_messages)
        if combined not in (prescription.warnings or ""):
            prescription.warnings = ((prescription.warnings or "") + f"\n{combined}").strip()
            prescription.save(update_fields=["warnings", "updated_at"])

    return alerts


@transaction.atomic
def apply_protocol_to_visit(*, protocol: ClinicalProtocol, visit, actor=None) -> dict:
    if protocol.species and protocol.species != visit.pet.species:
        raise ValueError(f"protocol species {protocol.species} does not match pet species {visit.pet.species}")

    created_diagnosis = None
    if protocol.diagnosis_title:
        diagnosis, _ = Diagnosis.objects.get_or_create(
            visit=visit,
            title=protocol.diagnosis_title,
            defaults={
                "code": protocol.diagnosis_code,
                "is_primary": False,
            },
        )
        created_diagnosis = diagnosis

    weight_kg = visit.pet.weight_kg
    created_prescriptions: list[Prescription] = []
    for med_template in protocol.medication_templates.all():
        dose_mg = calculate_recommended_dose_mg(weight_kg=weight_kg, medication_template=med_template)
        prescription = Prescription.objects.create(
            visit=visit,
            medication_name=med_template.medication_name,
            dosage=f"{dose_mg} mg",
            frequency=med_template.frequency,
            duration_days=med_template.duration_days,
            route=med_template.route,
            warnings=med_template.warnings,
        )
        created_prescriptions.append(prescription)

    created_procedures: list[ProcedureOrder] = []
    for proc_template in protocol.procedure_templates.all():
        procedure = ProcedureOrder.objects.create(
            visit=visit,
            name=proc_template.name,
            instructions=proc_template.instructions,
            status=ProcedureOrder.ProcedureStatus.PLANNED,
            performed_by=actor if actor and actor.is_authenticated else None,
        )
        Task.objects.create(
            title=f"Perform procedure: {procedure.name}",
            description=procedure.instructions,
            task_type=Task.TaskType.PROCEDURE,
            status=Task.TaskStatus.TODO,
            priority=Task.Priority.MEDIUM,
            visit=visit,
            assigned_to=actor if actor and actor.is_authenticated else None,
        )
        created_procedures.append(procedure)

    return {
        "protocol_id": protocol.id,
        "visit_id": visit.id,
        "diagnosis_id": created_diagnosis.id if created_diagnosis else None,
        "prescriptions_created": len(created_prescriptions),
        "procedures_created": len(created_procedures),
    }


@transaction.atomic
def create_checklist_for_procedure(*, procedure_order, template: ProcedureChecklistTemplate):
    checklist, created = ProcedureChecklist.objects.get_or_create(
        procedure_order=procedure_order,
        template=template,
        defaults={"status": ProcedureChecklist.ChecklistStatus.TODO},
    )
    if not created:
        return checklist

    for template_item in template.items.all():
        ProcedureChecklistItem.objects.create(
            checklist=checklist,
            title=template_item.title,
            is_required=template_item.is_required,
        )
    return checklist


@transaction.atomic
def complete_checklist_item(*, checklist_item, actor=None):
    if checklist_item.is_completed:
        checklist_item.checklist.mark_done_if_completed()
        return checklist_item

    checklist_item.is_completed = True
    checklist_item.completed_at = checklist_item.completed_at or timezone.now()
    checklist_item.completed_by = actor if actor and actor.is_authenticated else checklist_item.completed_by
    checklist_item.save(update_fields=["is_completed", "completed_at", "completed_by", "updated_at"])
    checklist_item.checklist.mark_done_if_completed()
    return checklist_item
