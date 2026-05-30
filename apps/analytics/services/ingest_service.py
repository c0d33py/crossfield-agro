"""
Ingestion services for analytics. Both functions are write-only and fast —
they do not run inside the rollup or query path.
"""

from __future__ import annotations

import ipaddress

from django.db import transaction

from apps.analytics.models import Event, PageView


def _truncate_ip(ip: str | None) -> str:
    """Reduce IP to /24 (v4) or /48 (v6) for privacy."""
    if not ip:
        return ""
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            return str(ipaddress.ip_network(f"{ip}/24", strict=False).network_address)
        return str(ipaddress.ip_network(f"{ip}/48", strict=False).network_address)
    except ValueError:
        return ""


@transaction.atomic
def record_pageview(
    *,
    path: str,
    referrer: str = "",
    session_key: str = "",
    user=None,
    ip: str | None = None,
    user_agent: str = "",
) -> PageView:
    return PageView.objects.create(
        path=path[:400],
        referrer=referrer[:600],
        session_key=session_key,
        user=user if (user and user.is_authenticated) else None,
        ip_prefix=_truncate_ip(ip),
        user_agent=user_agent[:300],
    )


@transaction.atomic
def record_event(
    *,
    name: str,
    path: str = "",
    session_key: str = "",
    user=None,
    metadata: dict | None = None,
) -> Event:
    return Event.objects.create(
        name=name[:80],
        path=path[:400],
        session_key=session_key,
        user=user if (user and user.is_authenticated) else None,
        metadata=metadata or {},
    )
