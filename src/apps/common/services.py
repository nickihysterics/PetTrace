from __future__ import annotations

import json
from decimal import Decimal

from .models import FeatureFlag, SystemSetting


def get_system_setting(key: str) -> SystemSetting | None:
    return SystemSetting.objects.filter(key=key, is_active=True).first()


def get_setting_string(key: str, default: str = "") -> str:
    setting = get_system_setting(key)
    if setting is None:
        return default
    return setting.value_text or default


def get_setting_bool(key: str, default: bool = False) -> bool:
    setting = get_system_setting(key)
    if setting is None:
        return default
    if setting.value_type == SystemSetting.ValueType.BOOLEAN:
        return str(setting.value_text).strip().lower() in {"1", "true", "yes", "on"}
    return str(setting.value_text).strip().lower() in {"1", "true", "yes", "on"}


def get_setting_int(key: str, default: int = 0) -> int:
    setting = get_system_setting(key)
    if setting is None:
        return default
    try:
        return int(setting.value_text)
    except (TypeError, ValueError):
        return default


def get_setting_decimal(key: str, default: Decimal | str = "0") -> Decimal:
    default_value = Decimal(str(default))
    setting = get_system_setting(key)
    if setting is None:
        return default_value
    try:
        return Decimal(setting.value_text)
    except Exception:
        return default_value


def get_setting_json(key: str, default=None):
    if default is None:
        default = {}
    setting = get_system_setting(key)
    if setting is None:
        return default
    if setting.value_type == SystemSetting.ValueType.JSON:
        return setting.value_json or default
    try:
        return json.loads(setting.value_text)
    except Exception:
        return default


def is_feature_enabled(code: str, default: bool = False) -> bool:
    flag = FeatureFlag.objects.filter(code=code).first()
    if flag is None:
        return default
    return bool(flag.enabled)
