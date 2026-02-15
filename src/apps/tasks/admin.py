from django.contrib import admin

from .models import Notification, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "task_type", "status", "priority", "assigned_to", "due_at"]
    list_filter = ["task_type", "status", "priority"]
    search_fields = ["title", "description", "visit__id", "lab_order__id"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "recipient", "channel", "title", "status", "sent_at"]
    list_filter = ["channel", "status"]
    search_fields = ["title", "recipient__email"]
