"""
Lightweight first-party analytics.

PageView: one row per page request from a JS beacon (or server-side push).
Event: arbitrary tracked actions (add-to-cart, signup, etc.) keyed by name.
DailyRollup: aggregated counts per path per day. Built nightly by Celery.

Per .claude/rules/performance.md: ingestion endpoint must be cheap; rollup is
async; we never block the request path on analytics writes.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class PageView(models.Model):
    path = models.CharField(max_length=400, db_index=True)
    referrer = models.CharField(max_length=600, blank=True)

    session_key = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Django session key for uniqueness checks.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    # IP truncated to /24 (v4) or /48 (v6) for privacy — never store full IP for analytics
    ip_prefix = models.CharField(max_length=45, blank=True, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["path", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.path}"


class Event(models.Model):
    """
    Custom event with optional metadata. Use sparingly — high-volume events
    should aggregate via DailyRollup rather than persisting every occurrence.
    """

    name = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Short event name, e.g. 'add_to_cart', 'checkout_start'.",
    )
    path = models.CharField(max_length=400, blank=True, db_index=True)

    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name", "-created_at"]),
            models.Index(fields=["session_key", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} @ {self.created_at:%Y-%m-%d %H:%M}"


class DailyRollup(models.Model):
    """Per-path counts aggregated by a Celery beat task at end of day."""

    path = models.CharField(max_length=400, db_index=True)
    date = models.DateField(db_index=True)

    views = models.PositiveIntegerField(default=0)
    unique_sessions = models.PositiveIntegerField(default=0)
    events = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "path"]
        constraints = [
            models.UniqueConstraint(fields=["path", "date"], name="rollup_unique_path_date"),
        ]
        indexes = [models.Index(fields=["-date", "path"])]

    def __str__(self) -> str:
        return f"{self.date} {self.path} — {self.views} views / {self.unique_sessions} sessions"
