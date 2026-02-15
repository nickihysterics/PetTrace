from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.visits.models import Prescription

from .services import evaluate_prescription_contraindications


@receiver(post_save, sender=Prescription)
def evaluate_contraindications_on_prescription_save(sender, instance, **kwargs):
    evaluate_prescription_contraindications(instance)
