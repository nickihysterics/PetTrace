from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создает группы RBAC по умолчанию и назначает базовые права."

    def handle(self, *args, **options):
        role_permissions = {
            "administrator": None,
            "registrar": [
                "view_branch", "view_cabinet",
                "view_service", "view_hospitalward", "view_hospitalbed",
                "view_owner", "add_owner", "change_owner",
                "view_pet", "add_pet", "change_pet",
                "view_consentdocument", "add_consentdocument", "change_consentdocument",
                "view_ownertag", "add_ownertag", "change_ownertag",
                "view_ownertagassignment", "add_ownertagassignment", "change_ownertagassignment",
                "view_communicationlog", "add_communicationlog", "change_communicationlog",
                "view_reminder", "add_reminder", "change_reminder",
                "dispatch_communication",
                "view_appointment", "add_appointment", "change_appointment",
                "view_visit", "add_visit", "change_visit",
                "view_hospitalization", "add_hospitalization", "change_hospitalization",
                "view_hospitalbedstay", "view_hospitalvitalrecord", "add_hospitalvitalrecord", "change_hospitalvitalrecord",
                "view_hospitalprocedureplan", "add_hospitalprocedureplan", "change_hospitalprocedureplan",
                "view_visitevent",
                "view_medicationadministration", "add_medicationadministration", "change_medicationadministration",
                "view_diagnosiscatalog", "view_symptomcatalog",
                "view_laborder", "view_specimen", "view_labresultvalue",
                "view_specimenrecollection", "view_labparameterreference",
                "view_clinicaldocument", "add_clinicaldocument", "change_clinicaldocument",
                "view_documenttemplate", "view_generateddocument",
                "view_invoice",
            ],
            "veterinarian": [
                "view_branch", "view_cabinet", "view_equipment", "view_servicerequirement", "view_service",
                "view_hospitalward", "view_hospitalbed",
                "view_appointment", "add_appointment", "change_appointment",
                "view_visit", "add_visit", "change_visit", "close_visit",
                "view_hospitalization", "add_hospitalization", "change_hospitalization",
                "view_hospitalbedstay", "view_hospitalvitalrecord", "add_hospitalvitalrecord", "change_hospitalvitalrecord",
                "view_hospitalprocedureplan", "add_hospitalprocedureplan", "change_hospitalprocedureplan",
                "view_visitevent",
                "view_diagnosis", "add_diagnosis", "change_diagnosis",
                "view_observation", "add_observation", "change_observation",
                "view_prescription", "add_prescription", "change_prescription",
                "view_medicationadministration", "add_medicationadministration", "change_medicationadministration",
                "view_procedureorder", "add_procedureorder", "change_procedureorder",
                "view_laborder", "add_laborder", "change_laborder",
                "view_labtest", "add_labtest", "change_labtest",
                "view_specimen", "add_specimen", "change_specimen",
                "view_specimenrecollection", "add_specimenrecollection", "change_specimenrecollection",
                "view_specimentube", "add_specimentube", "change_specimentube",
                "view_containerlabel", "add_containerlabel", "change_containerlabel",
                "view_labresultvalue", "add_labresultvalue", "change_labresultvalue",
                "view_labparameterreference",
                "view_tube",
                "view_clinicaldocument", "add_clinicaldocument", "change_clinicaldocument",
                "view_documenttemplate", "view_generateddocument",
                "view_diagnosiscatalog", "add_diagnosiscatalog", "change_diagnosiscatalog",
                "view_symptomcatalog", "add_symptomcatalog", "change_symptomcatalog",
                "view_clinicalprotocol", "add_clinicalprotocol", "change_clinicalprotocol", "apply_clinical_protocol",
                "view_protocolmedicationtemplate", "add_protocolmedicationtemplate", "change_protocolmedicationtemplate",
                "view_protocolproceduretemplate", "add_protocolproceduretemplate", "change_protocolproceduretemplate",
                "view_contraindicationrule", "add_contraindicationrule", "change_contraindicationrule",
                "view_clinicalalert", "add_clinicalalert", "change_clinicalalert",
                "view_procedurechecklisttemplate", "add_procedurechecklisttemplate", "change_procedurechecklisttemplate",
                "view_procedurechecklisttemplateitem", "add_procedurechecklisttemplateitem", "change_procedurechecklisttemplateitem",
                "view_procedurechecklist", "add_procedurechecklist", "change_procedurechecklist",
                "view_procedurechecklistitem", "add_procedurechecklistitem", "change_procedurechecklistitem",
                "view_task", "change_task",
                "view_notification",
            ],
            "assistant": [
                "view_branch", "view_cabinet", "view_equipment",
                "view_service", "view_hospitalward", "view_hospitalbed",
                "view_appointment", "change_appointment",
                "view_visit", "change_visit",
                "view_hospitalization", "add_hospitalization", "change_hospitalization",
                "view_hospitalbedstay", "view_hospitalvitalrecord", "add_hospitalvitalrecord", "change_hospitalvitalrecord",
                "view_hospitalprocedureplan", "add_hospitalprocedureplan", "change_hospitalprocedureplan",
                "view_visitevent",
                "view_procedureorder", "add_procedureorder", "change_procedureorder",
                "view_medicationadministration", "add_medicationadministration", "change_medicationadministration",
                "view_specimen", "add_specimen", "change_specimen",
                "view_specimenrecollection", "add_specimenrecollection", "change_specimenrecollection",
                "view_laborder", "change_laborder",
                "view_specimentube", "add_specimentube", "change_specimentube",
                "view_containerlabel", "add_containerlabel", "change_containerlabel",
                "view_tube",
                "view_clinicaldocument", "add_clinicaldocument", "change_clinicaldocument",
                "view_documenttemplate", "view_generateddocument",
                "view_procedurechecklist", "add_procedurechecklist", "change_procedurechecklist",
                "view_procedurechecklistitem", "add_procedurechecklistitem", "change_procedurechecklistitem",
                "view_task", "add_task", "change_task",
                "view_notification",
            ],
            "lab_technician": [
                "view_branch", "view_cabinet", "view_equipment", "view_equipmenttype", "view_hospitalward", "view_hospitalbed",
                "view_laborder", "change_laborder",
                "view_labtest", "change_labtest",
                "view_specimen", "change_specimen",
                "view_specimenrecollection", "add_specimenrecollection", "change_specimenrecollection",
                "view_specimentube", "add_specimentube", "change_specimentube",
                "view_containerlabel", "add_containerlabel", "change_containerlabel",
                "view_specimenevent", "add_specimenevent",
                "view_labresultvalue", "add_labresultvalue", "change_labresultvalue",
                "view_labparameterreference",
                "view_tube",
                "view_clinicaldocument", "add_clinicaldocument", "change_clinicaldocument",
                "view_documenttemplate", "view_generateddocument",
                "view_task", "change_task",
                "view_notification",
                "approve_lab_result",
            ],
            "inventory_manager": [
                "view_branch", "view_cabinet",
                "view_hospitalward", "view_hospitalbed",
                "view_inventoryitem", "add_inventoryitem", "change_inventoryitem",
                "view_batch", "add_batch", "change_batch",
                "view_stockmovement", "add_stockmovement", "change_stockmovement",
                "view_tube", "change_tube",
                "view_specimentube",
                "view_equipmenttype", "add_equipmenttype", "change_equipmenttype",
                "view_equipment", "add_equipment", "change_equipment",
                "view_servicerequirement", "view_servicerequirementequipment",
                "write_off_stock",
            ],
            "cashier": [
                "view_branch",
                "view_owner",
                "view_pet",
                "view_visit",
                "view_invoice", "add_invoice", "change_invoice",
                "view_invoiceline", "add_invoiceline", "change_invoiceline",
                "view_payment", "add_payment", "change_payment",
                "view_paymentadjustment",
                "view_priceitem", "add_priceitem", "change_priceitem",
                "view_discountrule", "add_discountrule", "change_discountrule",
                "view_generateddocument",
            ],
        }

        all_permissions = Permission.objects.all()

        for role, permission_codes in role_permissions.items():
            group, _ = Group.objects.get_or_create(name=role)
            if permission_codes is None:
                group.permissions.set(all_permissions)
                group.save()
                self.stdout.write(self.style.SUCCESS(f"Роль '{role}' синхронизирована со всеми правами"))
                continue

            permissions = Permission.objects.filter(codename__in=permission_codes)
            found_codes = set(permissions.values_list("codename", flat=True))
            missing_codes = sorted(set(permission_codes) - found_codes)
            if missing_codes:
                self.stdout.write(
                    self.style.WARNING(
                        f"Для роли '{role}' не найдены коды прав: {', '.join(missing_codes)}"
                    )
                )

            group.permissions.set(permissions)
            group.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Роль '{role}' синхронизирована: назначено прав {permissions.count()}"
                )
            )
