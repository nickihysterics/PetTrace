from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from .models import AuditLog


class AuditLogMiddleware:
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if request.method not in self.MUTATING_METHODS:
            return response
        if not request.path.startswith("/api/"):
            return response
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return response

        try:
            AuditLog.objects.create(
                actor=request.user,
                action=AuditLog.Action.API_MUTATION,
                model_label="http.request",
                object_pk=request.path,
                reason=f"HTTP {request.method}",
                changes={
                    "method": request.method,
                    "status_code": response.status_code,
                    "query_params": request.GET.dict(),
                },
                ip_address=self._extract_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        except Exception:
            # Не прерываем бизнес-операцию, если запись аудита завершилась ошибкой.
            return response

        return response

    @staticmethod
    def _extract_ip(request: HttpRequest) -> str | None:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
