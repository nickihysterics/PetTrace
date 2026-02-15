from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from . import localization  # noqa: F401

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.frontend.urls")),
    path("health/", include("apps.common.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include("apps.common.api_urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.facilities.urls")),
    path("api/", include("apps.owners.urls")),
    path("api/", include("apps.pets.urls")),
    path("api/", include("apps.crm.urls")),
    path("api/", include("apps.visits.urls")),
    path("api/", include("apps.clinical.urls")),
    path("api/", include("apps.labs.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.reports.urls")),
]
