from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import PublicUUIDModel, TimeStampedModel

from .managers import UserManager


class User(PublicUUIDModel, TimeStampedModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    job_title = models.CharField(max_length=128, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class UserAccessProfile(PublicUUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="access_profile",
    )
    home_branch = models.ForeignKey(
        "facilities.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="home_users",
    )
    allowed_branches = models.ManyToManyField(
        "facilities.Branch",
        blank=True,
        related_name="access_profiles",
    )
    allowed_cabinets = models.ManyToManyField(
        "facilities.Cabinet",
        blank=True,
        related_name="access_profiles",
    )
    limit_to_assigned_cabinets = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self) -> str:
        return f"Access profile: {self.user.email}"


class UserMFAProfile(PublicUUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="mfa_profile",
    )
    secret_key = models.CharField(max_length=64, blank=True)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self) -> str:
        return f"MFA profile: {self.user.email}"
