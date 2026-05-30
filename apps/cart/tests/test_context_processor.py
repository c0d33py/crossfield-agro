"""Regression tests for the cart_summary context processor."""

from __future__ import annotations

from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import RequestFactory

import pytest

from apps.cart.context_processors import cart_summary

pytestmark = pytest.mark.django_db


def _req():
    rf = RequestFactory()
    request = rf.get("/")
    # Stub a minimal session + anonymous user; selectors hit request.session.session_key
    request.session = type("S", (), {"session_key": None})()
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    return request


class TestCartSummaryContextProcessor:
    def test_returns_none_when_db_unavailable(self):
        """
        DB-down on a request shouldn't crash every page. Returning None lets
        the header render without a cart badge.
        """
        with patch(
            "apps.cart.context_processors.get_cart_for_request",
            side_effect=OperationalError("connection refused"),
        ):
            result = cart_summary(_req())
        assert result == {"cart_summary": None}

    def test_does_not_silence_programming_errors(self):
        """
        Regression: the old code swallowed *every* exception with bare
        `except Exception`, hiding real bugs (e.g. selector signature changes,
        AttributeError, ImportError). Only DatabaseError should be tolerated.
        """
        with patch(
            "apps.cart.context_processors.get_cart_for_request",
            side_effect=AttributeError("selector got renamed and no one noticed"),
        ):
            with pytest.raises(AttributeError):
                cart_summary(_req())
