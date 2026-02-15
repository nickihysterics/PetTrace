from django.urls import path

from .views import HealthCheckView, MetricsView

urlpatterns = [
    path("", HealthCheckView.as_view(), name="health-check"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
]
