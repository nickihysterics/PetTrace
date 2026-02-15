from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache

REPORTS_CACHE_PREFIX = "reports"
REPORTS_CACHE_TTL = getattr(settings, "REPORTS_CACHE_TTL", 120)


def _version_cache_key(domain: str) -> str:
    return f"{REPORTS_CACHE_PREFIX}:version:{domain}"


def _safe_int(value, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_domain_version(domain: str) -> int:
    key = _version_cache_key(domain)
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=None)
        return 1
    return _safe_int(current, default=1)


def bump_domain_version(domain: str) -> None:
    key = _version_cache_key(domain)
    try:
        cache.incr(key)
    except ValueError:
        current = get_domain_version(domain)
        cache.set(key, current + 1, timeout=None)


def build_report_cache_key(report_name: str, params: dict, domains: tuple[str, ...]) -> str:
    versions = {domain: get_domain_version(domain) for domain in sorted(domains)}
    source = json.dumps(
        {
            "report": report_name,
            "params": params,
            "versions": versions,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return f"{REPORTS_CACHE_PREFIX}:payload:{report_name}:{digest}"


def get_or_set_report_payload(
    *,
    report_name: str,
    params: dict,
    domains: tuple[str, ...],
    builder: Callable[[], dict],
) -> dict:
    cache_key = build_report_cache_key(report_name=report_name, params=params, domains=domains)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    payload = builder()
    cache.set(cache_key, payload, timeout=REPORTS_CACHE_TTL)
    return payload
