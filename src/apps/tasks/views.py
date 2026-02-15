from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import decorators, response
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.viewsets import RBACModelViewSet
from apps.users.access import (
    ensure_user_can_access_branch_cabinet,
    is_unrestricted_user,
    restrict_queryset_for_user_scope,
)

from .models import Notification, Task
from .serializers import NotificationSerializer, TaskSerializer


class TaskViewSet(RBACModelViewSet):
    queryset = Task.objects.select_related("assigned_to", "visit", "lab_order").all()
    serializer_class = TaskSerializer
    filterset_fields = ["task_type", "status", "priority", "assigned_to", "visit", "lab_order"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_at", "created_at", "priority"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if is_unrestricted_user(user):
            return queryset

        visit_bound = restrict_queryset_for_user_scope(
            queryset=queryset.filter(visit__isnull=False),
            user=user,
            branch_field="visit__branch",
            cabinet_field="visit__cabinet",
        )
        lab_bound = restrict_queryset_for_user_scope(
            queryset=queryset.filter(visit__isnull=True, lab_order__isnull=False),
            user=user,
            branch_field="lab_order__visit__branch",
            cabinet_field="lab_order__visit__cabinet",
        )
        detached = queryset.filter(visit__isnull=True, lab_order__isnull=True)
        return (visit_bound | lab_bound | detached).distinct()

    def perform_create(self, serializer):
        visit = serializer.validated_data.get("visit")
        lab_order = serializer.validated_data.get("lab_order")
        ref_visit = visit or getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(ref_visit, "branch", None),
                cabinet=getattr(ref_visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    def perform_update(self, serializer):
        visit = serializer.validated_data.get("visit", serializer.instance.visit)
        lab_order = serializer.validated_data.get("lab_order", serializer.instance.lab_order)
        ref_visit = visit or getattr(lab_order, "visit", None)
        try:
            ensure_user_can_access_branch_cabinet(
                user=self.request.user,
                branch=getattr(ref_visit, "branch", None),
                cabinet=getattr(ref_visit, "cabinet", None),
            )
        except ValidationError as exc:
            raise DRFValidationError(exc.messages[0] if hasattr(exc, "messages") else str(exc))
        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="complete")
    @transaction.atomic
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = Task.TaskStatus.DONE
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at", "updated_at"])
        return response.Response(self.get_serializer(task).data)


class NotificationViewSet(RBACModelViewSet):
    queryset = Notification.objects.select_related("recipient").all()
    serializer_class = NotificationSerializer
    filterset_fields = ["channel", "status", "recipient"]
    search_fields = ["title", "body", "recipient__email"]
    ordering_fields = ["created_at", "sent_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_unrestricted_user(self.request.user):
            return queryset
        return queryset.filter(recipient=self.request.user)
