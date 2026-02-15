from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeatureFlagViewSet, SystemSettingViewSet

router = DefaultRouter()
router.register("common/settings", SystemSettingViewSet, basename="system-setting")
router.register("common/feature-flags", FeatureFlagViewSet, basename="feature-flag")

urlpatterns = [
    path("", include(router.urls)),
]
