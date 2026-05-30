"""Inject current cart summary into every template via context processor."""

from __future__ import annotations

import logging

from django.db.utils import DatabaseError

from apps.cart.selectors import get_cart_for_request, get_cart_summary

logger = logging.getLogger(__name__)


def cart_summary(request) -> dict:
    # Pre-migration / DB-down: don't break every page render with a 500.
    # Anything else is a real bug — let it bubble so it gets fixed, not swallowed.
    try:
        cart = get_cart_for_request(request)
    except DatabaseError:
        logger.exception("cart_summary: DB error during cart lookup")
        return {"cart_summary": None}
    return {"cart_summary": get_cart_summary(cart)}
