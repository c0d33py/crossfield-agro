"""
Auto-log Django admin actions + auth events.

Other apps can also call apps.audit.services.log_action() directly for
business-domain actions (refunds, order transitions, etc.).
"""

from __future__ import annotations

import logging

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.audit.models import AuditAction
from apps.audit.services import log_action

logger = logging.getLogger(__name__)

User = get_user_model()


# --- Django admin log mirror ---

ADMIN_ACTION_MAP = {
    ADDITION: AuditAction.CREATE,
    CHANGE: AuditAction.UPDATE,
    DELETION: AuditAction.DELETE,
}


@receiver(post_save, sender=LogEntry)
def _mirror_admin_log(sender, instance: LogEntry, created: bool, **kwargs) -> None:
    if not created:
        return
    action = ADMIN_ACTION_MAP.get(instance.action_flag, AuditAction.OTHER)
    log_action(
        action=action,
        actor=instance.user,
        target=None,  # LogEntry has the type as a CT id, set fields explicitly below
        description=f"Admin: {instance.object_repr}"[:400],
        metadata={
            "admin_log_id": instance.pk,
            "change_message": instance.change_message,
            "content_type_id": instance.content_type_id,
            "object_id": instance.object_id,
            "object_repr": instance.object_repr,
        },
    )


# --- Auth events ---


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs) -> None:
    log_action(action=AuditAction.LOGIN, actor=user, target=user, request=request)


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs) -> None:
    if user is not None:
        log_action(action=AuditAction.LOGOUT, actor=user, target=user, request=request)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs) -> None:
    # Don't log the password — only the identity attempted
    username = credentials.get("username") or credentials.get("email") or "<unknown>"
    log_action(
        action=AuditAction.LOGIN_FAILED,
        description=f"Failed login attempt for {username}",
        metadata={"username": username},
        request=request,
    )
