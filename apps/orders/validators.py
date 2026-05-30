from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.orders.models import ALLOWED_TRANSITIONS


class InvalidOrderTransition(ValidationError):
    pass


def validate_transition(*, current: str, to_state: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if to_state not in allowed:
        raise InvalidOrderTransition(
            f"Illegal transition {current} -> {to_state}. Allowed: {sorted(allowed)}"
        )
