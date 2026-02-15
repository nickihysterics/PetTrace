from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class UsersApiPermissionTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.regular_user = user_model.objects.create_user(
            email="user.permissions@pettrace.local",
            password="test",
        )
        self.admin_user = user_model.objects.create_superuser(
            email="admin.permissions@pettrace.local",
            password="test",
        )

    def test_regular_user_cannot_list_users(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
