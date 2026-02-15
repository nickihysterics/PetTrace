from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "actor", "action", "model_label", "object_pk", "ip_address"]
    list_filter = ["action", "model_label", "created_at"]
    search_fields = ["model_label", "object_pk", "actor__email", "reason"]
