from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CommunicationLogViewSet,
    OwnerTagAssignmentViewSet,
    OwnerTagViewSet,
    ReminderViewSet,
)

router = DefaultRouter()
router.register("crm/tags", OwnerTagViewSet, basename="crm-tag")
router.register("crm/tag-assignments", OwnerTagAssignmentViewSet, basename="crm-tag-assignment")
router.register("crm/communications", CommunicationLogViewSet, basename="crm-communication")
router.register("crm/reminders", ReminderViewSet, basename="crm-reminder")

urlpatterns = [
    path("", include(router.urls)),
]
