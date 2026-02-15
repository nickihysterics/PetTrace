from celery import shared_task

from .services import dispatch_due_communications


@shared_task
def dispatch_due_communications_task() -> int:
    return dispatch_due_communications(limit=100)
