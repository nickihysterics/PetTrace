from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserAccessProfile, UserMFAProfile


class UserAccessProfileInline(admin.StackedInline):
    model = UserAccessProfile
    can_delete = False
    extra = 0
    filter_horizontal = ("allowed_branches", "allowed_cabinets")


class UserMFAProfileInline(admin.StackedInline):
    model = UserMFAProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "is_superuser", "groups"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("first_name", "last_name", "phone", "job_title")}),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )

    inlines = [UserAccessProfileInline, UserMFAProfileInline]
    search_fields = ["email", "first_name", "last_name"]


@admin.register(UserAccessProfile)
class UserAccessProfileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "home_branch",
        "limit_to_assigned_cabinets",
        "updated_at",
    ]
    list_filter = ["home_branch", "limit_to_assigned_cabinets"]
    search_fields = ["user__email", "notes"]
    filter_horizontal = ["allowed_branches", "allowed_cabinets"]


@admin.register(UserMFAProfile)
class UserMFAProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "is_enabled", "updated_at"]
    list_filter = ["is_enabled"]
    search_fields = ["user__email"]
