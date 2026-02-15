from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from apps.billing.models import Invoice, InvoiceLine, Payment, PaymentAdjustment, PriceItem
from apps.facilities.models import Branch, Cabinet
from apps.inventory.models import Batch, InventoryItem, StockMovement
from apps.labs.models import (
    ContainerLabel,
    LabOrder,
    LabResultValue,
    LabTest,
    Specimen,
    SpecimenEvent,
    SpecimenTube,
    Tube,
)
from apps.owners.models import ConsentDocument, Owner
from apps.pets.models import Pet
from apps.tasks.models import Notification, Task
from apps.visits.models import (
    Appointment,
    Diagnosis,
    Observation,
    Prescription,
    ProcedureOrder,
    Visit,
)

DEMO_MARKER = "[DEMO]"
DEMO_BULK_MARKER = "[DEMO-BULK]"
DEMO_OWNER_PHONE = "+79990000001"
DEMO_MICROCHIP = "900000000000001"
DEMO_USER_PASSWORD = "pettrace123"
DEMO_DATETIME = timezone.make_aware(datetime(2026, 2, 1, 10, 0))
DEMO_BULK_TUBE_CODE = "DEMO-BULK-EDTA-2ML"
DEMO_BULK_BATCH_LOT = "LOT-DEMO-BULK-EDTA-2026"
DEMO_BULK_ITEM_SKU = "DEMO-BULK-EDTA-2ML"


class Command(BaseCommand):
    help = "Заполняет базу согласованными демо-данными для PetTrace."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить ранее созданные демо-данные перед заполнением.",
        )
        parser.add_argument(
            "--bulk-cases",
            type=int,
            default=0,
            help="Создать дополнительный крупный набор демо-данных (число кейсов).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Распределить bulk-данные на указанное количество дней.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo_data()

        created = Counter()
        bulk_cases = max(int(options.get("bulk_cases") or 0), 0)
        days = max(int(options.get("days") or 90), 1)

        users = self._seed_users(created)
        facilities = self._seed_facilities(created)
        owner = self._seed_owner(created)
        self._seed_consent(owner, created)
        pet = self._seed_pet(owner, created)

        visit = self._seed_visit(owner, pet, users, facilities, created)
        self._seed_appointment(owner, pet, visit, users, facilities, created)
        self._seed_medical_data(visit, users, created)

        lab_order = self._seed_labs(visit, users, created)
        self._seed_inventory(lab_order, users, created)

        invoice = self._seed_billing(visit, owner, created)
        self._seed_tasks_and_notifications(visit, lab_order, users, created)

        if bulk_cases:
            self._seed_bulk_demo_data(
                users=users,
                facilities=facilities,
                created=created,
                bulk_cases=bulk_cases,
                days=days,
            )

        self.stdout.write(self.style.SUCCESS("Демо-данные готовы."))
        self.stdout.write(
            (
                f"Owner #{owner.id}, Pet #{pet.id}, Visit #{visit.id}, "
                f"LabOrder #{lab_order.id}, Invoice #{invoice.id}"
            )
        )
        for entity, count in sorted(created.items()):
            self.stdout.write(f"  {entity}: +{count}")

    def _seed_users(self, created: Counter):
        User = get_user_model()
        specs = [
            {
                "email": "registrar@pettrace.local",
                "first_name": "Regina",
                "last_name": "Desk",
                "job_title": "Registrar",
                "group": "registrar",
            },
            {
                "email": "vet@pettrace.local",
                "first_name": "Victor",
                "last_name": "Doctor",
                "job_title": "Veterinarian",
                "group": "veterinarian",
            },
            {
                "email": "assistant@pettrace.local",
                "first_name": "Alice",
                "last_name": "Nurse",
                "job_title": "Assistant",
                "group": "assistant",
            },
            {
                "email": "lab@pettrace.local",
                "first_name": "Leo",
                "last_name": "Lab",
                "job_title": "Lab Technician",
                "group": "lab_technician",
            },
            {
                "email": "inventory@pettrace.local",
                "first_name": "Ira",
                "last_name": "Stock",
                "job_title": "Inventory Manager",
                "group": "inventory_manager",
            },
            {
                "email": "cashier@pettrace.local",
                "first_name": "Cas",
                "last_name": "Hanna",
                "job_title": "Cashier",
                "group": "cashier",
            },
        ]

        users = {}
        for spec in specs:
            user, is_new = User.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "job_title": spec["job_title"],
                    "is_active": True,
                },
            )
            if is_new:
                user.set_password(DEMO_USER_PASSWORD)
                user.save(update_fields=["password"])
                created["users"] += 1
            elif not user.check_password(DEMO_USER_PASSWORD):
                user.set_password(DEMO_USER_PASSWORD)
                user.save(update_fields=["password"])

            dirty_fields = []
            for field in ["first_name", "last_name", "job_title", "is_active"]:
                value = spec[field] if field in spec else True
                if field == "is_active":
                    value = True
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    dirty_fields.append(field)
            if dirty_fields:
                user.save(update_fields=dirty_fields + ["updated_at"])

            group = Group.objects.filter(name=spec["group"]).first()
            if group and not user.groups.filter(id=group.id).exists():
                user.groups.add(group)

            users[spec["group"]] = user

        return users

    def _seed_owner(self, created: Counter):
        owner = Owner.objects.filter(phone=DEMO_OWNER_PHONE).first()
        defaults = {
            "first_name": "Nikolay",
            "last_name": "Petrov",
            "email": "owner.demo@pettrace.local",
            "address": "Moscow, Demo Street 1",
            "notes": f"{DEMO_MARKER} Regular gastro follow-up patient.",
            "discount_percent": Decimal("5.00"),
            "is_blacklisted": False,
        }
        if owner is None:
            owner = Owner.objects.create(phone=DEMO_OWNER_PHONE, **defaults)
            created["owners"] += 1
        else:
            for field, value in defaults.items():
                setattr(owner, field, value)
            owner.save(update_fields=list(defaults.keys()) + ["updated_at"])
        return owner

    def _seed_facilities(self, created: Counter):
        branch, branch_created = Branch.objects.get_or_create(
            code="MAIN",
            defaults={
                "name": "Main branch",
                "is_active": True,
            },
        )
        if branch_created:
            created["branches"] += 1

        consult_cabinet, consult_created = Cabinet.objects.get_or_create(
            branch=branch,
            code="C101",
            defaults={
                "name": "Consult room",
                "cabinet_type": Cabinet.CabinetType.CONSULTATION,
                "capacity": 1,
                "is_active": True,
            },
        )
        if consult_created:
            created["cabinets"] += 1

        lab_cabinet, lab_created = Cabinet.objects.get_or_create(
            branch=branch,
            code="L201",
            defaults={
                "name": "Lab room",
                "cabinet_type": Cabinet.CabinetType.LAB,
                "capacity": 2,
                "is_active": True,
            },
        )
        if lab_created:
            created["cabinets"] += 1

        return {
            "branch": branch,
            "consult_cabinet": consult_cabinet,
            "lab_cabinet": lab_cabinet,
        }

    def _seed_consent(self, owner: Owner, created: Counter):
        consent, is_new = ConsentDocument.objects.get_or_create(
            owner=owner,
            consent_type=ConsentDocument.ConsentType.PERSONAL_DATA,
            defaults={
                "accepted_at": DEMO_DATETIME,
            },
        )
        if is_new:
            created["consents"] += 1
        elif consent.accepted_at != DEMO_DATETIME:
            consent.accepted_at = DEMO_DATETIME
            consent.revoked_at = None
            consent.save(update_fields=["accepted_at", "revoked_at", "updated_at"])

    def _seed_pet(self, owner: Owner, created: Counter):
        pet = Pet.objects.filter(microchip_id=DEMO_MICROCHIP).first()
        defaults = {
            "owner": owner,
            "name": "Milo",
            "species": Pet.Species.CAT,
            "breed": "British Shorthair",
            "sex": Pet.Sex.MALE,
            "birth_date": date(2021, 5, 20),
            "weight_kg": Decimal("4.80"),
            "allergies": "No known allergies",
            "vaccination_notes": "Core vaccines up to date",
            "insurance_number": "INS-DEMO-001",
            "status": Pet.PetStatus.ACTIVE,
        }
        if pet is None:
            pet = Pet.objects.create(microchip_id=DEMO_MICROCHIP, **defaults)
            created["pets"] += 1
        else:
            for field, value in defaults.items():
                setattr(pet, field, value)
            pet.save(update_fields=list(defaults.keys()) + ["updated_at"])
        return pet

    def _seed_visit(self, owner: Owner, pet: Pet, users: dict, facilities: dict, created: Counter):
        visit = Visit.objects.filter(
            pet=pet,
            owner=owner,
            chief_complaint=f"{DEMO_MARKER} Vomiting and low appetite",
        ).first()
        defaults = {
            "veterinarian": users["veterinarian"],
            "assistant": users["assistant"],
            "status": Visit.VisitStatus.IN_PROGRESS,
            "branch": facilities["branch"],
            "cabinet": facilities["consult_cabinet"],
            "room": "101",
            "scheduled_at": DEMO_DATETIME,
            "started_at": DEMO_DATETIME + timedelta(minutes=15),
            "chief_complaint": f"{DEMO_MARKER} Vomiting and low appetite",
            "anamnesis": "Symptoms started two days ago after diet change.",
            "physical_exam": "Mild dehydration, abdominal sensitivity.",
            "diagnosis_summary": "Acute gastroenteritis, moderate severity.",
            "recommendations": "Hydration, diet correction, follow-up in 24 hours.",
        }
        if visit is None:
            visit = Visit.objects.create(pet=pet, owner=owner, **defaults)
            created["visits"] += 1
        else:
            for field, value in defaults.items():
                setattr(visit, field, value)
            visit.save(update_fields=list(defaults.keys()) + ["updated_at"])
        return visit

    def _seed_medical_data(self, visit: Visit, users: dict, created: Counter):
        _, is_new = Diagnosis.objects.get_or_create(
            visit=visit,
            title="Acute gastroenteritis",
            defaults={
                "code": "K52",
                "description": "Likely diet-related gastrointestinal inflammation.",
                "is_primary": True,
            },
        )
        if is_new:
            created["diagnoses"] += 1

        _, is_new = Observation.objects.get_or_create(
            visit=visit,
            name="Body temperature",
            defaults={"value": "39.2", "unit": "C", "notes": "Slightly elevated"},
        )
        if is_new:
            created["observations"] += 1

        _, is_new = Prescription.objects.get_or_create(
            visit=visit,
            medication_name="Enterosorbent",
            defaults={
                "dosage": "1 sachet",
                "frequency": "BID",
                "duration_days": 3,
                "route": "oral",
                "warnings": "Give between meals",
            },
        )
        if is_new:
            created["prescriptions"] += 1

        _, is_new = ProcedureOrder.objects.get_or_create(
            visit=visit,
            name="IV fluid therapy",
            defaults={
                "instructions": "250 ml balanced solution over 90 minutes",
                "status": ProcedureOrder.ProcedureStatus.IN_PROGRESS,
                "performed_by": users["assistant"],
            },
        )
        if is_new:
            created["procedures"] += 1

    def _seed_appointment(
        self,
        owner: Owner,
        pet: Pet,
        visit: Visit,
        users: dict,
        facilities: dict,
        created: Counter,
    ):
        appointment, is_new = Appointment.objects.get_or_create(
            owner=owner,
            pet=pet,
            start_at=DEMO_DATETIME,
            defaults={
                "veterinarian": users["veterinarian"],
                "created_by": users["registrar"],
                "service_type": "Primary consultation",
                "branch": facilities["branch"],
                "cabinet": facilities["consult_cabinet"],
                "room": "101",
                "status": Appointment.AppointmentStatus.IN_ROOM,
                "duration_minutes": 30,
                "end_at": DEMO_DATETIME + timedelta(minutes=30),
                "queue_number": 1,
                "checked_in_at": DEMO_DATETIME + timedelta(minutes=5),
                "visit": visit,
                "notes": f"{DEMO_MARKER} Appointment linked to active visit",
            },
        )
        if is_new:
            created["appointments"] += 1
        else:
            appointment.veterinarian = users["veterinarian"]
            appointment.created_by = users["registrar"]
            appointment.service_type = "Primary consultation"
            appointment.branch = facilities["branch"]
            appointment.cabinet = facilities["consult_cabinet"]
            appointment.room = "101"
            appointment.status = Appointment.AppointmentStatus.IN_ROOM
            appointment.duration_minutes = 30
            appointment.end_at = DEMO_DATETIME + timedelta(minutes=30)
            appointment.queue_number = 1
            appointment.checked_in_at = DEMO_DATETIME + timedelta(minutes=5)
            appointment.visit = visit
            appointment.notes = f"{DEMO_MARKER} Appointment linked to active visit"
            appointment.save(
                update_fields=[
                    "veterinarian",
                    "created_by",
                    "service_type",
                    "branch",
                    "cabinet",
                    "room",
                    "status",
                    "duration_minutes",
                    "end_at",
                    "queue_number",
                    "checked_in_at",
                    "visit",
                    "notes",
                    "updated_at",
                ]
            )

    def _seed_labs(self, visit: Visit, users: dict, created: Counter):
        lab_order, is_new = LabOrder.objects.get_or_create(
            visit=visit,
            notes=f"{DEMO_MARKER} GI baseline check",
            defaults={
                "ordered_by": users["veterinarian"],
                "status": LabOrder.LabOrderStatus.IN_PROCESS,
                "ordered_at": DEMO_DATETIME + timedelta(minutes=20),
                "sla_minutes": 90,
            },
        )
        if is_new:
            created["lab_orders"] += 1

        cbc_test, is_new = LabTest.objects.get_or_create(
            lab_order=lab_order,
            code="CBC",
            defaults={
                "name": "Complete blood count",
                "status": LabTest.LabTestStatus.IN_PROCESS,
                "specimen_type": "blood",
                "turnaround_minutes": 45,
            },
        )
        if is_new:
            created["lab_tests"] += 1

        _, is_new = LabTest.objects.get_or_create(
            lab_order=lab_order,
            code="BIO",
            defaults={
                "name": "Biochemistry panel",
                "status": LabTest.LabTestStatus.PLANNED,
                "specimen_type": "blood",
                "turnaround_minutes": 60,
            },
        )
        if is_new:
            created["lab_tests"] += 1

        specimen, is_new = Specimen.objects.get_or_create(
            lab_order=lab_order,
            specimen_type="blood",
            defaults={
                "status": Specimen.SpecimenStatus.COLLECTED,
                "collected_by": users["assistant"],
                "collected_at": DEMO_DATETIME + timedelta(minutes=30),
                "collection_room": "LAB-1",
            },
        )
        if is_new:
            created["specimens"] += 1

        tube, is_new = Tube.objects.get_or_create(
            code="DEMO-EDTA-2ML-001",
            defaults={
                "tube_type": Tube.TubeType.EDTA,
                "lot_number": "LOT-DEMO-EDTA-2026",
                "expires_at": date(2027, 12, 31),
            },
        )
        if is_new:
            created["tubes"] += 1

        _, is_new = SpecimenTube.objects.get_or_create(
            specimen=specimen,
            tube=tube,
            defaults={"quantity": 1},
        )
        if is_new:
            created["specimen_tubes"] += 1

        _, is_new = ContainerLabel.objects.get_or_create(
            specimen=specimen,
            defaults={
                "label_value": f"specimen:{specimen.public_id}",
                "printed_at": DEMO_DATETIME + timedelta(minutes=31),
            },
        )
        if is_new:
            created["labels"] += 1

        _, is_new = SpecimenEvent.objects.get_or_create(
            specimen=specimen,
            to_status=Specimen.SpecimenStatus.COLLECTED,
            notes=f"{DEMO_MARKER} specimen collected",
            defaults={
                "from_status": Specimen.SpecimenStatus.PLANNED,
                "actor": users["assistant"],
                "location": "LAB-1",
                "event_at": DEMO_DATETIME + timedelta(minutes=30),
            },
        )
        if is_new:
            created["specimen_events"] += 1

        _, is_new = LabResultValue.objects.update_or_create(
            lab_test=cbc_test,
            parameter_name="WBC",
            defaults={
                "value": "12.1",
                "unit": "10^9/L",
                "reference_range": "6.0-17.0",
                "flag": LabResultValue.Flag.NORMAL,
                "comment": "Within expected range",
            },
        )
        if is_new:
            created["lab_results"] += 1

        return lab_order

    def _seed_inventory(self, lab_order: LabOrder, users: dict, created: Counter):
        item, is_new = InventoryItem.objects.get_or_create(
            sku="DEMO-EDTA-2ML",
            defaults={
                "name": "EDTA tube 2ml",
                "category": InventoryItem.Category.LAB,
                "unit": "pcs",
                "min_stock": Decimal("20.00"),
                "is_active": True,
            },
        )
        if is_new:
            created["inventory_items"] += 1

        batch, is_new = Batch.objects.get_or_create(
            item=item,
            lot_number="LOT-DEMO-EDTA-2026",
            defaults={
                "expires_at": date(2027, 12, 31),
                "quantity_received": Decimal("200.00"),
                "quantity_available": Decimal("200.00"),
                "supplier": "DemoVetSupply",
            },
        )
        if is_new:
            created["batches"] += 1

        tube = Tube.objects.filter(code="DEMO-EDTA-2ML-001").first()
        if tube and tube.inventory_item_id != item.id:
            tube.inventory_item = item
            tube.save(update_fields=["inventory_item", "updated_at"])

        _, is_new = StockMovement.objects.get_or_create(
            item=item,
            batch=batch,
            movement_type=StockMovement.MovementType.INBOUND,
            reference_type="seed_demo",
            reference_id="DEMO-INBOUND-1",
            defaults={
                "quantity": Decimal("200.00"),
                "reason": "Demo initial stock",
                "moved_by": users["registrar"],
            },
        )
        if is_new:
            created["stock_movements"] += 1

        write_off, is_new = StockMovement.objects.get_or_create(
            item=item,
            batch=batch,
            movement_type=StockMovement.MovementType.WRITE_OFF,
            reference_type="seed_demo",
            reference_id=f"DEMO-LABORDER-{lab_order.id}",
            defaults={
                "quantity": Decimal("1.00"),
                "reason": "Demo specimen collection",
                "moved_by": users["assistant"],
            },
        )
        if is_new:
            created["stock_movements"] += 1
            if batch.quantity_available >= write_off.quantity:
                batch.quantity_available -= write_off.quantity
                batch.save(update_fields=["quantity_available", "updated_at"])

    def _seed_billing(self, visit: Visit, owner: Owner, created: Counter):
        consult, is_new = PriceItem.objects.get_or_create(
            code="DEMO-CONSULT-PRIMARY",
            defaults={
                "name": "Primary consultation",
                "amount": Decimal("2500.00"),
                "currency": "RUB",
                "is_active": True,
            },
        )
        if is_new:
            created["price_items"] += 1

        labs_package, is_new = PriceItem.objects.get_or_create(
            code="DEMO-LAB-GI",
            defaults={
                "name": "GI lab package",
                "amount": Decimal("1800.00"),
                "currency": "RUB",
                "is_active": True,
            },
        )
        if is_new:
            created["price_items"] += 1

        invoice, is_new = Invoice.objects.get_or_create(
            visit=visit,
            defaults={
                "status": Invoice.InvoiceStatus.DRAFT,
                "discount_percent": owner.discount_percent,
            },
        )
        if is_new:
            created["invoices"] += 1

        _, is_new = InvoiceLine.objects.get_or_create(
            invoice=invoice,
            description="Primary consultation",
            defaults={
                "price_item": consult,
                "quantity": Decimal("1.00"),
                "unit_price": consult.amount,
                "line_total": consult.amount,
            },
        )
        if is_new:
            created["invoice_lines"] += 1

        _, is_new = InvoiceLine.objects.get_or_create(
            invoice=invoice,
            description="GI lab package",
            defaults={
                "price_item": labs_package,
                "quantity": Decimal("1.00"),
                "unit_price": labs_package.amount,
                "line_total": labs_package.amount,
            },
        )
        if is_new:
            created["invoice_lines"] += 1

        invoice.discount_percent = owner.discount_percent
        invoice.recalculate_totals()
        invoice.status = Invoice.InvoiceStatus.POSTED
        if invoice.formed_at is None:
            invoice.formed_at = DEMO_DATETIME + timedelta(hours=2)
        if invoice.posted_at is None:
            invoice.posted_at = DEMO_DATETIME + timedelta(hours=2, minutes=5)
        invoice.save(
            update_fields=[
                "discount_percent",
                "subtotal_amount",
                "total_amount",
                "status",
                "formed_at",
                "posted_at",
                "updated_at",
            ]
        )

        payment, is_new = Payment.objects.get_or_create(
            invoice=invoice,
            method=Payment.PaymentMethod.CARD,
            external_id="DEMO-PAY-0001",
            defaults={
                "amount": invoice.total_amount,
                "paid_at": DEMO_DATETIME + timedelta(hours=2, minutes=10),
            },
        )
        if is_new:
            created["payments"] += 1
        elif payment.amount != invoice.total_amount:
            payment.amount = invoice.total_amount
            payment.save(update_fields=["amount", "updated_at"])

        total_paid = sum((p.amount for p in invoice.payments.all()), Decimal("0"))
        if total_paid >= invoice.total_amount > 0 and invoice.status != Invoice.InvoiceStatus.PAID:
            invoice.status = Invoice.InvoiceStatus.PAID
            invoice.save(update_fields=["status", "updated_at"])

        return invoice

    def _seed_tasks_and_notifications(
        self,
        visit: Visit,
        lab_order: LabOrder,
        users: dict,
        created: Counter,
    ):
        _, is_new = Task.objects.get_or_create(
            title="Repeat blood collection in 24h",
            visit=visit,
            defaults={
                "description": "Control CBC after hydration.",
                "task_type": Task.TaskType.FOLLOW_UP,
                "status": Task.TaskStatus.TODO,
                "priority": Task.Priority.HIGH,
                "lab_order": lab_order,
                "assigned_to": users["assistant"],
                "due_at": DEMO_DATETIME + timedelta(days=1),
            },
        )
        if is_new:
            created["tasks"] += 1

        _, is_new = Notification.objects.get_or_create(
            recipient=users["veterinarian"],
            title="Demo: CBC result available",
            defaults={
                "channel": Notification.Channel.IN_APP,
                "body": "WBC value has been saved for demo patient.",
                "payload": {"visit_id": visit.id, "lab_order_id": lab_order.id},
                "status": Notification.DeliveryStatus.PENDING,
            },
        )
        if is_new:
            created["notifications"] += 1

    def _bulk_visit_status(self, index: int) -> str:
        cycle = index % 10
        if cycle in {0, 1, 2, 3}:
            return Visit.VisitStatus.CLOSED
        if cycle in {4, 5}:
            return Visit.VisitStatus.COMPLETED
        if cycle in {6, 7}:
            return Visit.VisitStatus.IN_PROGRESS
        if cycle == 8:
            return Visit.VisitStatus.WAITING
        return Visit.VisitStatus.CANCELED

    def _bulk_appointment_status(self, visit_status: str) -> str:
        if visit_status in {Visit.VisitStatus.CLOSED, Visit.VisitStatus.COMPLETED}:
            return Appointment.AppointmentStatus.COMPLETED
        if visit_status == Visit.VisitStatus.IN_PROGRESS:
            return Appointment.AppointmentStatus.IN_ROOM
        if visit_status == Visit.VisitStatus.WAITING:
            return Appointment.AppointmentStatus.CHECKED_IN
        if visit_status == Visit.VisitStatus.CANCELED:
            return Appointment.AppointmentStatus.CANCELED
        return Appointment.AppointmentStatus.BOOKED

    def _seed_bulk_demo_data(
        self,
        *,
        users: dict,
        facilities: dict,
        created: Counter,
        bulk_cases: int,
        days: int,
    ) -> None:
        branch = facilities["branch"]
        consult_cabinet = facilities["consult_cabinet"]
        lab_cabinet = facilities["lab_cabinet"]

        veterinarian = users["veterinarian"]
        assistant = users["assistant"]
        registrar = users["registrar"]
        lab_technician = users.get("lab_technician") or assistant
        cashier = users.get("cashier") or registrar
        inventory_manager = users.get("inventory_manager") or assistant

        consult_price, is_new = PriceItem.objects.get_or_create(
            code="DEMO-BULK-CONSULT",
            defaults={
                "name": "Bulk consultation",
                "amount": Decimal("2200.00"),
                "currency": "RUB",
                "is_active": True,
            },
        )
        if is_new:
            created["price_items"] += 1

        procedure_price, is_new = PriceItem.objects.get_or_create(
            code="DEMO-BULK-PROCEDURE",
            defaults={
                "name": "Bulk procedure package",
                "amount": Decimal("1600.00"),
                "currency": "RUB",
                "is_active": True,
            },
        )
        if is_new:
            created["price_items"] += 1

        lab_price, is_new = PriceItem.objects.get_or_create(
            code="DEMO-BULK-LAB",
            defaults={
                "name": "Bulk lab package",
                "amount": Decimal("1900.00"),
                "currency": "RUB",
                "is_active": True,
            },
        )
        if is_new:
            created["price_items"] += 1

        bulk_item, is_new = InventoryItem.objects.get_or_create(
            sku=DEMO_BULK_ITEM_SKU,
            defaults={
                "name": "Demo bulk EDTA tube 2ml",
                "category": InventoryItem.Category.LAB,
                "unit": "pcs",
                "min_stock": Decimal("200.00"),
                "is_active": True,
            },
        )
        if is_new:
            created["inventory_items"] += 1

        bulk_batch, is_new = Batch.objects.get_or_create(
            item=bulk_item,
            lot_number=DEMO_BULK_BATCH_LOT,
            defaults={
                "expires_at": date(2028, 12, 31),
                "quantity_received": Decimal("10000.00"),
                "quantity_available": Decimal("10000.00"),
                "supplier": "DemoBulkSupplier",
            },
        )
        if is_new:
            created["batches"] += 1

        bulk_tube, is_new = Tube.objects.get_or_create(
            code=DEMO_BULK_TUBE_CODE,
            defaults={
                "tube_type": Tube.TubeType.EDTA,
                "lot_number": DEMO_BULK_BATCH_LOT,
                "expires_at": date(2028, 12, 31),
                "inventory_item": bulk_item,
            },
        )
        if is_new:
            created["tubes"] += 1
        elif bulk_tube.inventory_item_id != bulk_item.id:
            bulk_tube.inventory_item = bulk_item
            bulk_tube.save(update_fields=["inventory_item", "updated_at"])

        _, inbound_new = StockMovement.objects.get_or_create(
            item=bulk_item,
            batch=bulk_batch,
            movement_type=StockMovement.MovementType.INBOUND,
            reference_type="seed_demo_bulk",
            reference_id="DEMO-BULK-INBOUND",
            defaults={
                "quantity": Decimal("10000.00"),
                "reason": "Bulk demo initial stock",
                "moved_by": inventory_manager,
            },
        )
        if inbound_new:
            created["stock_movements"] += 1

        now = timezone.now()
        today = timezone.localdate()
        midnight = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        for index in range(1, bulk_cases + 1):
            case_code = f"{index:05d}"
            owner_phone = f"+79991{index:06d}"
            owner, owner_new = Owner.objects.update_or_create(
                phone=owner_phone,
                defaults={
                    "first_name": f"DemoOwner{case_code}",
                    "last_name": "Bulk",
                    "email": f"owner.bulk.{case_code}@pettrace.local",
                    "address": f"Demo City, Bulk Avenue {index}",
                    "notes": f"{DEMO_BULK_MARKER} Owner {case_code}",
                    "discount_percent": Decimal(str(index % 12)),
                    "is_blacklisted": False,
                    "preferred_branch": branch,
                },
            )
            if owner_new:
                created["owners"] += 1

            consent, consent_new = ConsentDocument.objects.get_or_create(
                owner=owner,
                consent_type=ConsentDocument.ConsentType.PERSONAL_DATA,
                defaults={"accepted_at": now - timedelta(days=index % days)},
            )
            if consent_new:
                created["consents"] += 1
            elif consent.revoked_at is not None:
                consent.revoked_at = None
                consent.save(update_fields=["revoked_at", "updated_at"])

            species = Pet.Species.DOG if index % 2 == 0 else Pet.Species.CAT
            pet, pet_new = Pet.objects.update_or_create(
                microchip_id=f"91{index:013d}",
                defaults={
                    "owner": owner,
                    "name": f"DemoPet{case_code}",
                    "species": species,
                    "breed": "Mixed",
                    "sex": Pet.Sex.MALE if index % 3 else Pet.Sex.FEMALE,
                    "birth_date": date(2019 + (index % 5), ((index % 12) + 1), ((index % 27) + 1)),
                    "weight_kg": Decimal("3.50") + Decimal(str((index % 70) / 10)),
                    "allergies": "" if index % 8 else "Protein intolerance",
                    "vaccination_notes": "Vaccines current",
                    "insurance_number": f"DEMO-BULK-INS-{case_code}",
                    "status": Pet.PetStatus.ACTIVE,
                },
            )
            if pet_new:
                created["pets"] += 1

            visit_day = index % days
            visit_start = midnight - timedelta(days=visit_day) + timedelta(
                hours=8 + (index % 10),
                minutes=(index * 11) % 60,
            )
            visit_status = self._bulk_visit_status(index)
            visit_started = visit_start + timedelta(minutes=10)
            visit_ended = None
            if visit_status in {
                Visit.VisitStatus.COMPLETED,
                Visit.VisitStatus.CLOSED,
                Visit.VisitStatus.CANCELED,
            }:
                visit_ended = visit_start + timedelta(minutes=55)

            visit, visit_new = Visit.objects.update_or_create(
                owner=owner,
                pet=pet,
                chief_complaint=f"{DEMO_BULK_MARKER} Case {case_code}",
                defaults={
                    "veterinarian": veterinarian,
                    "assistant": assistant,
                    "status": visit_status,
                    "branch": branch,
                    "cabinet": consult_cabinet,
                    "room": consult_cabinet.code,
                    "scheduled_at": visit_start,
                    "started_at": visit_started
                    if visit_status
                    in {
                        Visit.VisitStatus.IN_PROGRESS,
                        Visit.VisitStatus.COMPLETED,
                        Visit.VisitStatus.CLOSED,
                        Visit.VisitStatus.CANCELED,
                    }
                    else None,
                    "ended_at": visit_ended,
                    "anamnesis": "Bulk demo anamnesis",
                    "physical_exam": "Bulk demo physical exam",
                    "diagnosis_summary": "Bulk demo diagnosis summary",
                    "recommendations": "Bulk demo recommendations",
                },
            )
            if visit_new:
                created["visits"] += 1

            appointment_status = self._bulk_appointment_status(visit_status)
            appointment, appointment_new = Appointment.objects.update_or_create(
                owner=owner,
                pet=pet,
                start_at=visit_start,
                defaults={
                    "veterinarian": veterinarian,
                    "created_by": registrar,
                    "service_type": "Bulk consultation",
                    "branch": branch,
                    "cabinet": consult_cabinet,
                    "room": consult_cabinet.code,
                    "notes": f"{DEMO_BULK_MARKER} Appointment {case_code}",
                    "duration_minutes": 30,
                    "end_at": visit_start + timedelta(minutes=30),
                    "queue_number": (index % 60) + 1,
                    "checked_in_at": visit_start + timedelta(minutes=5)
                    if appointment_status
                    in {
                        Appointment.AppointmentStatus.CHECKED_IN,
                        Appointment.AppointmentStatus.IN_ROOM,
                        Appointment.AppointmentStatus.COMPLETED,
                    }
                    else None,
                    "completed_at": visit_ended
                    if appointment_status in {Appointment.AppointmentStatus.COMPLETED}
                    else None,
                    "status": appointment_status,
                    "visit": visit,
                },
            )
            if appointment_new:
                created["appointments"] += 1

            if visit_status != Visit.VisitStatus.CANCELED:
                _, diagnosis_new = Diagnosis.objects.update_or_create(
                    visit=visit,
                    title=f"{DEMO_BULK_MARKER} Diagnosis",
                    defaults={
                        "code": "D-BULK",
                        "description": f"Bulk diagnosis case {case_code}",
                        "is_primary": True,
                    },
                )
                if diagnosis_new:
                    created["diagnoses"] += 1

                _, observation_new = Observation.objects.update_or_create(
                    visit=visit,
                    name="Respiratory rate",
                    defaults={
                        "value": str(18 + (index % 10)),
                        "unit": "rpm",
                        "notes": f"{DEMO_BULK_MARKER} observation",
                    },
                )
                if observation_new:
                    created["observations"] += 1

                _, prescription_new = Prescription.objects.update_or_create(
                    visit=visit,
                    medication_name="BulkSupport",
                    defaults={
                        "dosage": f"{1 + (index % 3)} tablet",
                        "frequency": "BID",
                        "duration_days": 5 + (index % 3),
                        "route": "oral",
                        "warnings": "With food",
                    },
                )
                if prescription_new:
                    created["prescriptions"] += 1

                _, procedure_new = ProcedureOrder.objects.update_or_create(
                    visit=visit,
                    name="Bulk infusion",
                    defaults={
                        "instructions": "500 ml over 2h",
                        "status": ProcedureOrder.ProcedureStatus.DONE
                        if visit_status in {Visit.VisitStatus.CLOSED, Visit.VisitStatus.COMPLETED}
                        else ProcedureOrder.ProcedureStatus.IN_PROGRESS,
                        "performed_by": assistant,
                        "performed_at": visit_start + timedelta(minutes=40)
                        if visit_status in {Visit.VisitStatus.CLOSED, Visit.VisitStatus.COMPLETED}
                        else None,
                    },
                )
                if procedure_new:
                    created["procedures"] += 1

            lab_order = None
            if visit_status != Visit.VisitStatus.CANCELED and index % 3 != 0:
                done_lab = (
                    visit_status in {Visit.VisitStatus.CLOSED, Visit.VisitStatus.COMPLETED}
                    and index % 2 == 0
                )
                lab_status = (
                    LabOrder.LabOrderStatus.DONE
                    if done_lab
                    else LabOrder.LabOrderStatus.IN_PROCESS
                )
                lab_order, lab_order_new = LabOrder.objects.update_or_create(
                    visit=visit,
                    notes=f"{DEMO_BULK_MARKER} Lab order {case_code}",
                    defaults={
                        "ordered_by": veterinarian,
                        "status": lab_status,
                        "ordered_at": visit_start + timedelta(minutes=15),
                        "completed_at": visit_start + timedelta(minutes=95) if done_lab else None,
                        "sla_minutes": 120,
                    },
                )
                if lab_order_new:
                    created["lab_orders"] += 1

                cbc_status = (
                    LabTest.LabTestStatus.DONE
                    if done_lab
                    else LabTest.LabTestStatus.IN_PROCESS
                )
                cbc_test, cbc_new = LabTest.objects.update_or_create(
                    lab_order=lab_order,
                    code="CBC",
                    defaults={
                        "name": "Complete blood count",
                        "status": cbc_status,
                        "specimen_type": "blood",
                        "turnaround_minutes": 45,
                    },
                )
                if cbc_new:
                    created["lab_tests"] += 1

                bio_status = (
                    LabTest.LabTestStatus.DONE
                    if done_lab
                    else LabTest.LabTestStatus.PLANNED
                )
                bio_test, bio_new = LabTest.objects.update_or_create(
                    lab_order=lab_order,
                    code="BIO",
                    defaults={
                        "name": "Biochemistry panel",
                        "status": bio_status,
                        "specimen_type": "blood",
                        "turnaround_minutes": 60,
                    },
                )
                if bio_new:
                    created["lab_tests"] += 1

                specimen_status = (
                    Specimen.SpecimenStatus.DONE
                    if done_lab
                    else Specimen.SpecimenStatus.IN_PROCESS
                )
                specimen, specimen_new = Specimen.objects.update_or_create(
                    lab_order=lab_order,
                    specimen_type="blood",
                    defaults={
                        "status": specimen_status,
                        "collected_by": assistant,
                        "collected_at": visit_start + timedelta(minutes=20),
                        "received_at": visit_start + timedelta(minutes=30),
                        "in_process_at": visit_start + timedelta(minutes=45),
                        "done_at": visit_start + timedelta(minutes=90) if done_lab else None,
                        "collection_room": lab_cabinet.code,
                    },
                )
                if specimen_new:
                    created["specimens"] += 1

                _, specimen_tube_new = SpecimenTube.objects.get_or_create(
                    specimen=specimen,
                    tube=bulk_tube,
                    defaults={"quantity": 1},
                )
                if specimen_tube_new:
                    created["specimen_tubes"] += 1

                _, label_new = ContainerLabel.objects.update_or_create(
                    specimen=specimen,
                    defaults={
                        "label_value": f"bulk-specimen:{specimen.public_id}",
                        "printed_at": visit_start + timedelta(minutes=21),
                    },
                )
                if label_new:
                    created["labels"] += 1

                _, event_new = SpecimenEvent.objects.get_or_create(
                    specimen=specimen,
                    to_status=specimen_status,
                    notes=f"{DEMO_BULK_MARKER} event {case_code}",
                    defaults={
                        "from_status": Specimen.SpecimenStatus.PLANNED,
                        "actor": assistant,
                        "location": lab_cabinet.code,
                        "event_at": visit_start + timedelta(minutes=22),
                    },
                )
                if event_new:
                    created["specimen_events"] += 1

                flag = LabResultValue.Flag.NORMAL
                if index % 17 == 0:
                    flag = LabResultValue.Flag.CRITICAL
                elif index % 7 == 0:
                    flag = LabResultValue.Flag.HIGH

                _, result_new = LabResultValue.objects.update_or_create(
                    lab_test=cbc_test,
                    parameter_name="WBC",
                    defaults={
                        "value": str(6 + (index % 13)),
                        "unit": "10^9/L",
                        "reference_range": "6-17",
                        "flag": flag,
                        "comment": f"{DEMO_BULK_MARKER} result {case_code}",
                        "approved_by": lab_technician if done_lab else None,
                        "approved_at": visit_start + timedelta(minutes=95) if done_lab else None,
                    },
                )
                if result_new:
                    created["lab_results"] += 1

                _, bio_result_new = LabResultValue.objects.update_or_create(
                    lab_test=bio_test,
                    parameter_name="ALT",
                    defaults={
                        "value": str(35 + (index % 40)),
                        "unit": "U/L",
                        "reference_range": "20-100",
                        "flag": LabResultValue.Flag.NORMAL,
                        "comment": f"{DEMO_BULK_MARKER} bio result {case_code}",
                        "approved_by": lab_technician if done_lab else None,
                        "approved_at": visit_start + timedelta(minutes=95) if done_lab else None,
                    },
                )
                if bio_result_new:
                    created["lab_results"] += 1

                movement, movement_new = StockMovement.objects.get_or_create(
                    item=bulk_item,
                    batch=bulk_batch,
                    movement_type=StockMovement.MovementType.WRITE_OFF,
                    reference_type="specimen_tube",
                    reference_id=f"DEMO-BULK-SPECIMEN-{specimen.id}",
                    defaults={
                        "quantity": Decimal("1.00"),
                        "reason": "Bulk demo specimen collection",
                        "moved_by": assistant,
                    },
                )
                if movement_new:
                    created["stock_movements"] += 1
                    if bulk_batch.quantity_available >= movement.quantity:
                        bulk_batch.quantity_available -= movement.quantity
                        bulk_batch.save(update_fields=["quantity_available", "updated_at"])

            if visit_status != Visit.VisitStatus.CANCELED:
                invoice, invoice_new = Invoice.objects.get_or_create(
                    visit=visit,
                    defaults={
                        "status": Invoice.InvoiceStatus.DRAFT,
                        "discount_percent": owner.discount_percent,
                    },
                )
                if invoice_new:
                    created["invoices"] += 1

                line_specs = [
                    ("Bulk consultation", consult_price, Decimal("1.00")),
                    ("Bulk procedure package", procedure_price, Decimal("1.00")),
                ]
                if lab_order is not None:
                    line_specs.append(("Bulk lab package", lab_price, Decimal("1.00")))

                for description, price_item, quantity in line_specs:
                    _, line_new = InvoiceLine.objects.get_or_create(
                        invoice=invoice,
                        description=description,
                        defaults={
                            "price_item": price_item,
                            "quantity": quantity,
                            "unit_price": price_item.amount,
                            "line_total": quantity * price_item.amount,
                        },
                    )
                    if line_new:
                        created["invoice_lines"] += 1

                invoice.discount_percent = owner.discount_percent
                invoice.recalculate_totals()
                invoice.status = Invoice.InvoiceStatus.POSTED
                invoice.formed_at = visit_start + timedelta(hours=1, minutes=10)
                invoice.posted_at = visit_start + timedelta(hours=1, minutes=15)
                invoice.save(
                    update_fields=[
                        "discount_percent",
                        "subtotal_amount",
                        "total_amount",
                        "status",
                        "formed_at",
                        "posted_at",
                        "updated_at",
                    ]
                )
                Invoice.objects.filter(id=invoice.id).update(
                    created_at=visit_start + timedelta(hours=1),
                )

                should_be_paid = visit_status in {
                    Visit.VisitStatus.CLOSED,
                    Visit.VisitStatus.COMPLETED,
                }
                should_be_partial = visit_status in {
                    Visit.VisitStatus.IN_PROGRESS,
                    Visit.VisitStatus.WAITING,
                } and index % 2 == 0

                payment_amount = Decimal("0")
                if should_be_paid:
                    payment_amount = invoice.total_amount
                elif should_be_partial:
                    payment_amount = (invoice.total_amount / Decimal("2")).quantize(Decimal("0.01"))

                payment = None
                if payment_amount > 0:
                    payment, payment_new = Payment.objects.update_or_create(
                        invoice=invoice,
                        external_id=f"DEMO-BULK-PAY-{case_code}",
                        defaults={
                            "method": Payment.PaymentMethod.CARD
                            if index % 2
                            else Payment.PaymentMethod.CASH,
                            "amount": payment_amount,
                            "paid_at": visit_start + timedelta(hours=1, minutes=30),
                        },
                    )
                    if payment_new:
                        created["payments"] += 1

                if payment and should_be_paid and payment.amount >= invoice.total_amount:
                    if invoice.status != Invoice.InvoiceStatus.PAID:
                        invoice.status = Invoice.InvoiceStatus.PAID
                        invoice.save(update_fields=["status", "updated_at"])

                if payment and payment.amount > 0 and index % 19 == 0:
                    refund_amount = (payment.amount * Decimal("0.10")).quantize(Decimal("0.01"))
                    _, adjustment_new = PaymentAdjustment.objects.update_or_create(
                        payment=payment,
                        adjustment_type=PaymentAdjustment.AdjustmentType.REFUND,
                        reason=f"{DEMO_BULK_MARKER} refund {case_code}",
                        defaults={
                            "amount": refund_amount,
                            "adjusted_by": cashier,
                            "adjusted_at": visit_start + timedelta(hours=2),
                            "external_reference": f"DEMO-BULK-REF-{case_code}",
                        },
                    )
                    if adjustment_new:
                        created["payment_adjustments"] += 1
                elif payment and payment.amount > 0 and index % 23 == 0:
                    correction_amount = (payment.amount * Decimal("0.05")).quantize(Decimal("0.01"))
                    _, adjustment_new = PaymentAdjustment.objects.update_or_create(
                        payment=payment,
                        adjustment_type=PaymentAdjustment.AdjustmentType.CORRECTION,
                        reason=f"{DEMO_BULK_MARKER} correction {case_code}",
                        defaults={
                            "amount": correction_amount,
                            "adjusted_by": cashier,
                            "adjusted_at": visit_start + timedelta(hours=2),
                            "external_reference": f"DEMO-BULK-COR-{case_code}",
                        },
                    )
                    if adjustment_new:
                        created["payment_adjustments"] += 1

            task_status = (
                Task.TaskStatus.DONE
                if visit_status in {Visit.VisitStatus.CLOSED, Visit.VisitStatus.COMPLETED}
                else Task.TaskStatus.TODO
            )
            _, task_new = Task.objects.update_or_create(
                title=f"{DEMO_BULK_MARKER} Follow-up {case_code}",
                visit=visit,
                defaults={
                    "description": "Bulk demo follow-up task",
                    "task_type": Task.TaskType.FOLLOW_UP,
                    "status": task_status,
                    "priority": Task.Priority.MEDIUM if index % 4 else Task.Priority.HIGH,
                    "lab_order": lab_order,
                    "assigned_to": assistant if index % 2 else veterinarian,
                    "due_at": visit_start + timedelta(days=1),
                    "completed_at": visit_start + timedelta(hours=2)
                    if task_status == Task.TaskStatus.DONE
                    else None,
                },
            )
            if task_new:
                created["tasks"] += 1

            if index % 8 == 0:
                _, notification_new = Notification.objects.update_or_create(
                    recipient=veterinarian,
                    title=f"{DEMO_BULK_MARKER} Lab update {case_code}",
                    defaults={
                        "channel": Notification.Channel.IN_APP,
                        "body": "Bulk demo lab notification",
                        "payload": {"visit_id": visit.id},
                        "status": Notification.DeliveryStatus.PENDING,
                    },
                )
                if notification_new:
                    created["notifications"] += 1

    def _reset_demo_data(self):
        Notification.objects.filter(title__startswith=DEMO_BULK_MARKER).delete()
        Task.objects.filter(title__startswith=DEMO_BULK_MARKER).delete()
        Invoice.objects.filter(visit__chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        LabOrder.objects.filter(notes__startswith=DEMO_BULK_MARKER).delete()
        Appointment.objects.filter(notes__startswith=DEMO_BULK_MARKER).delete()
        ProcedureOrder.objects.filter(visit__chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        Prescription.objects.filter(visit__chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        Observation.objects.filter(visit__chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        Diagnosis.objects.filter(visit__chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        Visit.objects.filter(chief_complaint__startswith=DEMO_BULK_MARKER).delete()
        ConsentDocument.objects.filter(owner__notes__startswith=DEMO_BULK_MARKER).delete()
        Pet.objects.filter(insurance_number__startswith="DEMO-BULK-INS-").delete()
        Owner.objects.filter(notes__startswith=DEMO_BULK_MARKER).delete()
        StockMovement.objects.filter(reference_id__startswith="DEMO-BULK-").delete()
        StockMovement.objects.filter(reference_type="seed_demo_bulk").delete()
        SpecimenTube.objects.filter(tube__code=DEMO_BULK_TUBE_CODE).delete()
        Tube.objects.filter(code=DEMO_BULK_TUBE_CODE).delete()
        Batch.objects.filter(lot_number=DEMO_BULK_BATCH_LOT).delete()
        InventoryItem.objects.filter(sku=DEMO_BULK_ITEM_SKU).delete()
        PriceItem.objects.filter(code__startswith="DEMO-BULK-").delete()

        Payment.objects.filter(external_id="DEMO-PAY-0001").delete()
        InvoiceLine.objects.filter(
            description__in=["Primary consultation", "GI lab package"]
        ).delete()
        PriceItem.objects.filter(code__startswith="DEMO-").delete()
        SpecimenTube.objects.filter(tube__code="DEMO-EDTA-2ML-001").delete()
        Tube.objects.filter(code="DEMO-EDTA-2ML-001").delete()
        StockMovement.objects.filter(batch__lot_number="LOT-DEMO-EDTA-2026").delete()
        StockMovement.objects.filter(item__sku="DEMO-EDTA-2ML").delete()
        StockMovement.objects.filter(reference_type="seed_demo").delete()
        Batch.objects.filter(lot_number="LOT-DEMO-EDTA-2026").delete()
        InventoryItem.objects.filter(sku="DEMO-EDTA-2ML").delete()
        Notification.objects.filter(title__startswith="Demo:").delete()
        Task.objects.filter(title="Repeat blood collection in 24h").delete()
        LabResultValue.objects.filter(lab_test__lab_order__notes__startswith=DEMO_MARKER).delete()
        SpecimenEvent.objects.filter(notes__startswith=DEMO_MARKER).delete()
        ContainerLabel.objects.filter(label_value__startswith="specimen:").delete()
        Specimen.objects.filter(lab_order__notes__startswith=DEMO_MARKER).delete()
        LabTest.objects.filter(lab_order__notes__startswith=DEMO_MARKER).delete()
        LabOrder.objects.filter(notes__startswith=DEMO_MARKER).delete()
        Appointment.objects.filter(pet__microchip_id=DEMO_MICROCHIP).delete()
        Appointment.objects.filter(notes__startswith=DEMO_MARKER).delete()
        ProcedureOrder.objects.filter(visit__chief_complaint__startswith=DEMO_MARKER).delete()
        Prescription.objects.filter(visit__chief_complaint__startswith=DEMO_MARKER).delete()
        Observation.objects.filter(visit__chief_complaint__startswith=DEMO_MARKER).delete()
        Diagnosis.objects.filter(visit__chief_complaint__startswith=DEMO_MARKER).delete()
        Visit.objects.filter(pet__microchip_id=DEMO_MICROCHIP).delete()
        Visit.objects.filter(chief_complaint__startswith=DEMO_MARKER).delete()
        Pet.objects.filter(microchip_id=DEMO_MICROCHIP).delete()
        ConsentDocument.objects.filter(owner__phone=DEMO_OWNER_PHONE).delete()
        Owner.objects.filter(phone=DEMO_OWNER_PHONE).delete()

        User = get_user_model()
        demo_emails = [
            "registrar@pettrace.local",
            "vet@pettrace.local",
            "assistant@pettrace.local",
            "lab@pettrace.local",
            "inventory@pettrace.local",
            "cashier@pettrace.local",
        ]
        demo_user_ids = list(
            User.objects.filter(email__in=demo_emails).values_list("id", flat=True)
        )
        if demo_user_ids:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.token_blacklist_outstandingtoken')")
                has_token_table = cursor.fetchone()[0] is not None
                if has_token_table:
                    cursor.execute(
                        """
                        DELETE FROM token_blacklist_blacklistedtoken
                        WHERE token_id IN (
                            SELECT id FROM token_blacklist_outstandingtoken WHERE user_id = ANY(%s)
                        )
                        """,
                        [demo_user_ids],
                    )
                    cursor.execute(
                        "DELETE FROM token_blacklist_outstandingtoken WHERE user_id = ANY(%s)",
                        [demo_user_ids],
                    )

        User.objects.filter(email__in=demo_emails).delete()
