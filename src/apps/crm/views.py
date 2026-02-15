from rest_framework import decorators, response, status

from apps.common.viewsets import RBACModelViewSet

from .models import CommunicationLog, OwnerTag, OwnerTagAssignment, Reminder
from .serializers import (
    CommunicationLogSerializer,
    OwnerTagAssignmentSerializer,
    OwnerTagSerializer,
    ReminderSerializer,
)
from .services import dispatch_communication, dispatch_due_communications


class OwnerTagViewSet(RBACModelViewSet):
    queryset = OwnerTag.objects.all()
    serializer_class = OwnerTagSerializer
    search_fields = ["name"]


class OwnerTagAssignmentViewSet(RBACModelViewSet):
    queryset = OwnerTagAssignment.objects.select_related("owner", "tag").all()
    serializer_class = OwnerTagAssignmentSerializer
    filterset_fields = ["owner", "tag"]


class CommunicationLogViewSet(RBACModelViewSet):
    queryset = CommunicationLog.objects.select_related("owner", "pet", "visit", "sent_by").all()
    serializer_class = CommunicationLogSerializer
    filterset_fields = ["owner", "pet", "visit", "channel", "direction", "status"]
    search_fields = ["owner__phone", "owner__last_name", "subject", "body"]
    action_permission_map = {
        "dispatch_single": ["dispatch_communication"],
        "dispatch_due": ["dispatch_communication"],
    }

    @decorators.action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_single(self, request, pk=None):
        communication = self.get_object()
        dispatch_communication(
            communication=communication,
            actor=request.user if request.user.is_authenticated else None,
        )
        return response.Response(self.get_serializer(communication).data)

    @decorators.action(detail=False, methods=["post"], url_path="dispatch-due")
    def dispatch_due(self, request):
        sent = dispatch_due_communications(limit=100)
        return response.Response({"sent": sent}, status=status.HTTP_200_OK)


class ReminderViewSet(RBACModelViewSet):
    queryset = Reminder.objects.select_related("owner", "pet", "visit").all()
    serializer_class = ReminderSerializer
    filterset_fields = ["owner", "pet", "visit", "reminder_type", "status"]
    search_fields = ["owner__phone", "owner__last_name", "message"]
