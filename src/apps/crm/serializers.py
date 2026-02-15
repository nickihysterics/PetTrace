from rest_framework import serializers

from .models import CommunicationLog, OwnerTag, OwnerTagAssignment, Reminder


class OwnerTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerTag
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class OwnerTagAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerTagAssignment
        fields = "__all__"
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class CommunicationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationLog
        fields = "__all__"
        read_only_fields = ["id", "public_id", "sent_at", "created_at", "updated_at"]


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = "__all__"
        read_only_fields = ["id", "public_id", "sent_at", "created_at", "updated_at"]
