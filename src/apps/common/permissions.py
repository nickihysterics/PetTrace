from rest_framework.permissions import SAFE_METHODS, DjangoModelPermissions


class ClinicModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def _format_permission(self, model_cls, codename: str) -> str:
        if "." in codename:
            return codename
        return f"{model_cls._meta.app_label}.{codename}"

    def _get_action_permissions(self, request, view, model_cls):
        action = getattr(view, "action", None)
        if not action:
            return None

        action_map = getattr(view, "action_permission_map", {})
        if action in action_map:
            return [self._format_permission(model_cls, code) for code in action_map[action]]

        standard_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}
        if action in standard_actions:
            return None

        model_name = model_cls._meta.model_name
        if request.method in SAFE_METHODS:
            return [self._format_permission(model_cls, f"view_{model_name}")]
        if getattr(view, "detail", False):
            return [self._format_permission(model_cls, f"change_{model_name}")]
        return [self._format_permission(model_cls, f"add_{model_name}")]

    def has_permission(self, request, view):
        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        if getattr(view, "_ignore_model_permissions", False):
            return True

        queryset = self._queryset(view)
        perms = self._get_action_permissions(request, view, queryset.model)
        if perms is None:
            perms = self.get_required_permissions(request.method, queryset.model)
        return request.user.has_perms(perms)
