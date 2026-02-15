from django.contrib import admin

from .models import Pet, PetAttachment


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "species", "breed", "owner", "microchip_id", "status"]
    list_filter = ["species", "status", "sex"]
    search_fields = ["name", "owner__last_name", "owner__phone", "microchip_id"]


@admin.register(PetAttachment)
class PetAttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "pet", "title", "created_at"]
    search_fields = ["pet__name", "title"]
