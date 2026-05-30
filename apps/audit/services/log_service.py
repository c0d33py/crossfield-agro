"""
Single entry point for writing audit log entries. Designed to be cheap and
hard-to-misuse — callers pass any Django model instance as `target` and we
snapshot the type, id, and str() representation.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.audit.models import AuditAction, AuditLogEntry

logger = logging.getLogger(__name__)


def _target_meta(target: Any) -> tuple[str, str, str]:
    """Return (target_type, target_id, target_label) for any model or None."""
    if target is None:
        return "", "", ""
    try:
        meta = target._meta
        target_type = f"{meta.app_label}.{meta.object_name}"
        # Prefer .uuid if present, else .pk
        ident = getattr(target, "uuid", None) or target.pk
        target_id = str(ident) if ident is not None else ""
        target_label = str(target)[:200]
        return target_type, target_id, target_label
    except Exception:
        return "", "", str(target)[:200]


def _actor_label(actor) -> str:
    if actor is None or not getattr(actor, "is_authenticated", False):
        return ""
    # Try email > username > id
    return (
        getattr(actor, "email", None) or getattr(actor, "username", None) or f"user:{actor.pk}"
    )[:200]


@transaction.atomic
def log_action(
    *,
    action: str,
    actor: Any = None,
    target: Any = None,
    description: str = "",
    metadata: dict | None = None,
    request=None,
) -> AuditLogEntry:
    """
    Persist an audit log entry. Never raises on failure — best-effort logging,
    we don't want audit writes to break the calling code path.
    """
    target_type, target_id, target_label = _target_meta(target)
    ip = None
    user_agent = ""
    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]

    try:
        return AuditLogEntry.objects.create(
            action=action,
            actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
            actor_label=_actor_label(actor),
            target_type=target_type[:120],
            target_id=target_id[:64],
            target_label=target_label,
            description=description[:400],
            metadata=metadata or {},
            ip_address=ip,
            user_agent=user_agent,
        )
    except Exception as exc:
        logger.error("audit.log_action failed: %s", exc, exc_info=True)
        # Return a not-persisted instance so callers needn't check for None
        return AuditLogEntry(action=action, description=description[:400])


# Convenience constant export
__all__ = ["log_action", "AuditAction"]
