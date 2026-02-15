from django.contrib import admin

from .models import ConsentDocument, Owner


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "last_name",
        "first_name",
        "phone",
        "preferred_branch",
        "is_blacklisted",
        "discount_percent",
    ]
    list_filter = ["is_blacklisted", "preferred_branch"]
    search_fields = ["last_name", "first_name", "phone", "email", "preferred_branch__name", "preferred_branch__code"]


@admin.register(ConsentDocument)
class ConsentDocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "consent_type", "accepted_at", "revoked_at"]
    list_filter = ["consent_type"]
    search_fields = ["owner__last_name", "owner__phone"]
