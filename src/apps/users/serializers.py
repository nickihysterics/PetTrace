from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import User, UserAccessProfile, UserMFAProfile


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class UserAccessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessProfile
        fields = [
            "id",
            "public_id",
            "user",
            "home_branch",
            "allowed_branches",
            "allowed_cabinets",
            "limit_to_assigned_cabinets",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        branch_values = attrs.get("allowed_branches")
        cabinet_values = attrs.get("allowed_cabinets")

        branch_ids = set(branch_values.values_list("id", flat=True)) if branch_values is not None else None
        if branch_ids is None and self.instance is not None:
            branch_ids = set(self.instance.allowed_branches.values_list("id", flat=True))

        if cabinet_values is not None and branch_ids:
            invalid_cabinets = [cabinet.id for cabinet in cabinet_values if cabinet.branch_id not in branch_ids]
            if invalid_cabinets:
                raise serializers.ValidationError(
                    "Каждый выбранный кабинет должен принадлежать одному из разрешенных филиалов"
                )

        return attrs


class UserMFAProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMFAProfile
        fields = [
            "id",
            "public_id",
            "user",
            "is_enabled",
            "backup_codes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), required=False)
    access_profile = UserAccessProfileSerializer(read_only=True)
    mfa_profile = UserMFAProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "public_id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "job_title",
            "is_active",
            "is_staff",
            "groups",
            "access_profile",
            "mfa_profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class SessionLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    otp_code = serializers.CharField(write_only=True, required=False, allow_blank=True)


class SessionLoginResponseSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    csrf_token = serializers.CharField(read_only=True)
    mfa_required = serializers.BooleanField(read_only=True)


class MFASetupResponseSerializer(serializers.Serializer):
    secret_key = serializers.CharField(read_only=True)
    otpauth_uri = serializers.CharField(read_only=True)


class MFAVerifySerializer(serializers.Serializer):
    otp_code = serializers.CharField()
