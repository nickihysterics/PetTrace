from django.http import HttpResponse, JsonResponse
from django.views import View

from apps.common.models import FeatureFlag, SystemSetting
from apps.common.serializers import FeatureFlagSerializer, SystemSettingSerializer
from apps.common.viewsets import RBACModelViewSet


class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


class MetricsView(View):
    def get(self, request):
        from apps.labs.models import LabOrder
        from apps.tasks.models import Task
        from apps.visits.models import Visit

        lines = []

        visit_total = Visit.objects.count()
        lines.append("# HELP pettrace_visits_total Total visits count")
        lines.append("# TYPE pettrace_visits_total gauge")
        lines.append(f"pettrace_visits_total {visit_total}")
        for status_code in Visit.VisitStatus.values:
            value = Visit.objects.filter(status=status_code).count()
            lines.append(f'pettrace_visits_status{{status="{status_code}"}} {value}')

        lab_total = LabOrder.objects.count()
        lines.append("# HELP pettrace_lab_orders_total Total lab orders count")
        lines.append("# TYPE pettrace_lab_orders_total gauge")
        lines.append(f"pettrace_lab_orders_total {lab_total}")
        for status_code in LabOrder.LabOrderStatus.values:
            value = LabOrder.objects.filter(status=status_code).count()
            lines.append(f'pettrace_lab_orders_status{{status="{status_code}"}} {value}')

        task_total = Task.objects.count()
        lines.append("# HELP pettrace_tasks_total Total tasks count")
        lines.append("# TYPE pettrace_tasks_total gauge")
        lines.append(f"pettrace_tasks_total {task_total}")
        for status_code in Task.TaskStatus.values:
            value = Task.objects.filter(status=status_code).count()
            lines.append(f'pettrace_tasks_status{{status="{status_code}"}} {value}')

        return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; version=0.0.4")


class SystemSettingViewSet(RBACModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    filterset_fields = ["key", "value_type", "is_active"]
    search_fields = ["key", "description", "value_text"]


class FeatureFlagViewSet(RBACModelViewSet):
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    filterset_fields = ["code", "enabled"]
    search_fields = ["code", "name", "description"]
