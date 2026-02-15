from django.contrib import admin

from .models import CommunicationLog, OwnerTag, OwnerTagAssignment, Reminder


@admin.register(OwnerTag)
class OwnerTagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "color"]
    search_fields = ["name"]


@admin.register(OwnerTagAssignment)
class OwnerTagAssignmentAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "tag"]
    list_filter = ["tag"]
    search_fields = ["owner__phone", "owner__last_name", "tag__name"]


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "channel", "direction", "status", "scheduled_at", "sent_at"]
    list_filter = ["channel", "direction", "status"]
    search_fields = ["owner__phone", "owner__last_name", "subject", "body"]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "pet", "reminder_type", "status", "due_at", "sent_at"]
    list_filter = ["reminder_type", "status"]
    search_fields = ["owner__phone", "owner__last_name", "message"]
