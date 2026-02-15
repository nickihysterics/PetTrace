from django.contrib import admin

from .models import FeatureFlag, SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ["id", "key", "value_type", "value_text", "is_active"]
    list_filter = ["value_type", "is_active"]
    search_fields = ["key", "description", "value_text"]


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "enabled"]
    list_filter = ["enabled"]
    search_fields = ["code", "name", "description"]
