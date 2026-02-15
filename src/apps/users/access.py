from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import UserAccessProfile

ROLE_ADMINISTRATOR = "administrator"

ROLE_DEFAULT_CABINET_TYPES = {
    "registrar": {"CONSULTATION", "OTHER"},
    "veterinarian": {"CONSULTATION", "PROCEDURE", "SURGERY", "INPATIENT"},
    "assistant": {"CONSULTATION", "PROCEDURE", "INPATIENT"},
    "lab_technician": {"LAB"},
    "inventory_manager": {"LAB", "PROCEDURE", "SURGERY", "INPATIENT", "OTHER"},
    "cashier": {"CONSULTATION", "OTHER"},
}


def get_user_role_names(user) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    return set(user.groups.values_list("name", flat=True))


def is_unrestricted_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return ROLE_ADMINISTRATOR in get_user_role_names(user)


def get_user_access_profile(user) -> UserAccessProfile | None:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.access_profile
    except UserAccessProfile.DoesNotExist:
        return None


def get_role_default_cabinet_types(user) -> set[str] | None:
    role_names = get_user_role_names(user)
    if ROLE_ADMINISTRATOR in role_names:
        return None

    role_types: set[str] = set()
    has_policy = False
    for role_name in role_names:
        if role_name not in ROLE_DEFAULT_CABINET_TYPES:
            continue
        has_policy = True
        role_types.update(ROLE_DEFAULT_CABINET_TYPES[role_name])

    if not has_policy:
        return None
    return role_types


def _get_allowed_branch_ids(profile: UserAccessProfile | None) -> set[int]:
    if profile is None:
        return set()

    branch_ids = set(profile.allowed_branches.values_list("id", flat=True))
    if not branch_ids and profile.home_branch_id:
        branch_ids.add(profile.home_branch_id)
    return branch_ids


def _get_allowed_cabinet_ids(profile: UserAccessProfile | None) -> set[int]:
    if profile is None:
        return set()
    return set(profile.allowed_cabinets.values_list("id", flat=True))


def _cabinet_type_lookup(cabinet_field: str) -> str:
    if cabinet_field in {"id", "pk"}:
        return "cabinet_type"
    return f"{cabinet_field}__cabinet_type"


def _cabinet_null_lookup(cabinet_field: str) -> str | None:
    if cabinet_field in {"id", "pk"}:
        return None
    return f"{cabinet_field}__isnull"


def _build_cabinet_scope_q(
    *,
    cabinet_field: str,
    role_cabinet_types: set[str] | None,
    allowed_cabinet_ids: Iterable[int],
    limit_to_assigned_cabinets: bool,
    allow_unassigned: bool,
) -> Q | None:
    allowed_cabinet_ids = set(allowed_cabinet_ids)
    cabinet_lookup = f"{cabinet_field}__in"
    null_lookup = _cabinet_null_lookup(cabinet_field)
    type_lookup = _cabinet_type_lookup(cabinet_field)

    if limit_to_assigned_cabinets:
        if not allowed_cabinet_ids:
            if allow_unassigned and null_lookup:
                return Q(**{null_lookup: True})
            return Q(pk__in=[])
        query = Q(**{cabinet_lookup: allowed_cabinet_ids})
        if allow_unassigned and null_lookup:
            query |= Q(**{null_lookup: True})
        return query

    cabinet_query: Q | None = None
    if allowed_cabinet_ids:
        cabinet_query = Q(**{cabinet_lookup: allowed_cabinet_ids})

    if role_cabinet_types is not None:
        role_query = Q(**{f"{type_lookup}__in": sorted(role_cabinet_types)})
        cabinet_query = role_query if cabinet_query is None else (cabinet_query | role_query)

    if cabinet_query is None:
        return None

    if allow_unassigned and null_lookup:
        cabinet_query |= Q(**{null_lookup: True})
    return cabinet_query


def restrict_queryset_for_user_scope(
    *,
    queryset,
    user,
    branch_field: str | None = None,
    cabinet_field: str | None = None,
    allow_unassigned: bool = True,
):
    if not user or not user.is_authenticated:
        return queryset.none()
    if is_unrestricted_user(user):
        return queryset

    profile = get_user_access_profile(user)
    allowed_branch_ids = _get_allowed_branch_ids(profile)
    allowed_cabinet_ids = _get_allowed_cabinet_ids(profile)
    role_cabinet_types = get_role_default_cabinet_types(user)

    access_query = Q()
    has_scope = False

    if branch_field and allowed_branch_ids:
        branch_query = Q(**{f"{branch_field}__in": allowed_branch_ids})
        if allow_unassigned:
            branch_query |= Q(**{f"{branch_field}__isnull": True})
        access_query &= branch_query
        has_scope = True

    if cabinet_field:
        cabinet_query = _build_cabinet_scope_q(
            cabinet_field=cabinet_field,
            role_cabinet_types=role_cabinet_types,
            allowed_cabinet_ids=allowed_cabinet_ids,
            limit_to_assigned_cabinets=bool(
                profile and profile.limit_to_assigned_cabinets
            ),
            allow_unassigned=allow_unassigned,
        )
        if cabinet_query is not None:
            access_query &= cabinet_query
            has_scope = True

    if not has_scope:
        return queryset
    return queryset.filter(access_query)


def user_can_access_branch(*, user, branch) -> bool:
    if branch is None:
        return True
    if is_unrestricted_user(user):
        return True

    profile = get_user_access_profile(user)
    allowed_branch_ids = _get_allowed_branch_ids(profile)
    if not allowed_branch_ids:
        return True
    return branch.id in allowed_branch_ids


def user_can_access_cabinet(*, user, cabinet) -> bool:
    if cabinet is None:
        return True
    if is_unrestricted_user(user):
        return True
    if not user_can_access_branch(user=user, branch=cabinet.branch):
        return False

    profile = get_user_access_profile(user)
    allowed_cabinet_ids = _get_allowed_cabinet_ids(profile)
    if profile and profile.limit_to_assigned_cabinets:
        return cabinet.id in allowed_cabinet_ids
    if cabinet.id in allowed_cabinet_ids:
        return True

    role_cabinet_types = get_role_default_cabinet_types(user)
    if role_cabinet_types is None:
        return True
    return cabinet.cabinet_type in role_cabinet_types


def ensure_user_can_access_branch_cabinet(*, user, branch=None, cabinet=None) -> None:
    if not user or not user.is_authenticated:
        raise ValidationError("Требуется авторизация пользователя")

    if not user_can_access_branch(user=user, branch=branch):
        raise ValidationError("Нет доступа к выбранному филиалу")

    if cabinet and not user_can_access_cabinet(user=user, cabinet=cabinet):
        raise ValidationError("Нет доступа к выбранному кабинету")
