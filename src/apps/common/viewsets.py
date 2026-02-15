from rest_framework import viewsets

from apps.users.access import restrict_queryset_for_user_scope

from .permissions import ClinicModelPermissions


class ScopedQuerysetMixin:
    scope_branch_field: str | None = None
    scope_cabinet_field: str | None = None
    scope_allow_unassigned: bool = True

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.scope_branch_field and not self.scope_cabinet_field:
            return queryset

        return restrict_queryset_for_user_scope(
            queryset=queryset,
            user=getattr(self.request, "user", None),
            branch_field=self.scope_branch_field,
            cabinet_field=self.scope_cabinet_field,
            allow_unassigned=self.scope_allow_unassigned,
        )


class RBACModelViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [ClinicModelPermissions]


class RBACReadOnlyModelViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [ClinicModelPermissions]
