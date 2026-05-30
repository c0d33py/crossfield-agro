from __future__ import annotations

import hmac

from django.core.exceptions import ValidationError


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


def require_signature(*, expected: str, received: str) -> None:
    if not constant_time_compare(expected, received):
        raise ValidationError("Invalid webhook signature")
