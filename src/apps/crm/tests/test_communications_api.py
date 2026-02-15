from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.crm.models import CommunicationLog
from apps.owners.models import Owner


class CommunicationDispatchTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin.crm@pettrace.local",
            password="test",
        )
        self.client.force_authenticate(self.user)

        self.owner = Owner.objects.create(first_name="CRM", last_name="Owner", phone="+79990000033")
        self.communication = CommunicationLog.objects.create(
            owner=self.owner,
            channel=CommunicationLog.Channel.EMAIL,
            direction=CommunicationLog.Direction.OUTBOUND,
            status=CommunicationLog.Status.PENDING,
            subject="Follow-up",
            body="Please come tomorrow",
            scheduled_at=timezone.now(),
        )

    def test_dispatch_single_communication(self):
        response = self.client.post(f"/api/crm/communications/{self.communication.id}/dispatch/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.communication.refresh_from_db()
        self.assertEqual(self.communication.status, CommunicationLog.Status.SENT)
        self.assertIsNotNone(self.communication.sent_at)

    def test_dispatch_due_bulk_action(self):
        response = self.client.post("/api/crm/communications/dispatch-due/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["sent"], 1)
