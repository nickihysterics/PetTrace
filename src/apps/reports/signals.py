from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.billing.models import Invoice, InvoiceLine, Payment, PaymentAdjustment
from apps.inventory.models import Batch, InventoryItem, StockMovement
from apps.labs.models import LabOrder, LabResultValue, LabTest, Specimen
from apps.visits.models import Appointment, Visit

from .cache import bump_domain_version


@receiver([post_save, post_delete], sender=LabOrder)
@receiver([post_save, post_delete], sender=LabTest)
@receiver([post_save, post_delete], sender=Specimen)
@receiver([post_save, post_delete], sender=LabResultValue)
def invalidate_labs_reports(**kwargs):
    bump_domain_version("labs")


@receiver([post_save, post_delete], sender=InventoryItem)
@receiver([post_save, post_delete], sender=Batch)
@receiver([post_save, post_delete], sender=StockMovement)
def invalidate_inventory_reports(**kwargs):
    bump_domain_version("inventory")


@receiver([post_save, post_delete], sender=Appointment)
@receiver([post_save, post_delete], sender=Visit)
def invalidate_appointments_reports(**kwargs):
    bump_domain_version("appointments")


@receiver([post_save, post_delete], sender=Invoice)
@receiver([post_save, post_delete], sender=InvoiceLine)
@receiver([post_save, post_delete], sender=Payment)
@receiver([post_save, post_delete], sender=PaymentAdjustment)
def invalidate_finance_reports(**kwargs):
    bump_domain_version("finance")
