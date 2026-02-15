from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GroupViewSet,
    MFADisableView,
    MFASetupView,
    MFAVerifyView,
    SessionLoginView,
    SessionLogoutView,
    SessionMeView,
    UserAccessProfileViewSet,
    UserMFAProfileViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")
router.register("user-access-profiles", UserAccessProfileViewSet, basename="user-access-profile")
router.register("user-mfa-profiles", UserMFAProfileViewSet, basename="user-mfa-profile")

urlpatterns = [
    path("auth/login/", SessionLoginView.as_view(), name="session-login"),
    path("auth/logout/", SessionLogoutView.as_view(), name="session-logout"),
    path("auth/me/", SessionMeView.as_view(), name="session-me"),
    path("auth/mfa/setup/", MFASetupView.as_view(), name="auth-mfa-setup"),
    path("auth/mfa/verify/", MFAVerifyView.as_view(), name="auth-mfa-verify"),
    path("auth/mfa/disable/", MFADisableView.as_view(), name="auth-mfa-disable"),
    path("", include(router.urls)),
]
