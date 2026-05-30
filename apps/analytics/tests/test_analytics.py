from __future__ import annotations

import json
from datetime import date

from django.urls import reverse

import pytest

from apps.analytics.models import DailyRollup, Event, PageView
from apps.analytics.services import record_event, record_pageview
from apps.analytics.services.ingest_service import _truncate_ip
from apps.analytics.tasks import rollup_daily

pytestmark = pytest.mark.django_db


class TestTruncateIp:
    def test_v4_truncated_to_24(self):
        assert _truncate_ip("203.0.113.42") == "203.0.113.0"

    def test_v6_truncated_to_48(self):
        out = _truncate_ip("2001:db8:1234:5678::1")
        assert out.startswith("2001:db8:1234:")

    def test_empty(self):
        assert _truncate_ip(None) == ""
        assert _truncate_ip("bogus") == ""


class TestRecordServices:
    def test_record_pageview_persists(self):
        pv = record_pageview(path="/products/", ip="203.0.113.42")
        assert PageView.objects.filter(pk=pv.pk).exists()
        assert pv.ip_prefix == "203.0.113.0"  # truncated

    def test_record_event_persists(self):
        ev = record_event(name="add_to_cart", path="/products/x/", metadata={"qty": 2})
        assert Event.objects.filter(pk=ev.pk).exists()
        assert ev.metadata == {"qty": 2}


class TestIngestionEndpoints:
    def test_pageview_endpoint_accepts_json(self, client):
        response = client.post(
            reverse("analytics:pageview"),
            data=json.dumps({"path": "/products/", "referrer": "/"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert PageView.objects.count() == 1

    def test_event_requires_name(self, client):
        response = client.post(
            reverse("analytics:event"),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert Event.objects.count() == 0

    def test_event_persists(self, client):
        response = client.post(
            reverse("analytics:event"),
            data=json.dumps({"name": "cta_click", "path": "/", "metadata": {"id": "buy"}}),
            content_type="application/json",
        )
        assert response.status_code == 200
        ev = Event.objects.first()
        assert ev.name == "cta_click"
        assert ev.metadata == {"id": "buy"}


class TestDailyRollup:
    def test_aggregates_views_and_events(self):
        # Create some same-day pageviews + events
        record_pageview(path="/p1/", session_key="s1")
        record_pageview(path="/p1/", session_key="s2")
        record_pageview(path="/p1/", session_key="s1")  # dup session
        record_pageview(path="/p2/", session_key="s3")
        record_event(name="x", path="/p1/")

        today_iso = date.today().isoformat()
        rollup_daily(today_iso)

        p1 = DailyRollup.objects.get(path="/p1/", date=date.today())
        assert p1.views == 3
        assert p1.unique_sessions == 2
        assert p1.events == 1

        p2 = DailyRollup.objects.get(path="/p2/", date=date.today())
        assert p2.views == 1

    def test_idempotent_upsert(self):
        record_pageview(path="/p/")
        today_iso = date.today().isoformat()
        rollup_daily(today_iso)
        rollup_daily(today_iso)  # second run
        assert DailyRollup.objects.filter(path="/p/", date=date.today()).count() == 1
