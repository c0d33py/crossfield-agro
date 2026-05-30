from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

import pytest

from apps.media_center.models import MediaCoverage, PressRelease, ReleaseStatus

pytestmark = pytest.mark.django_db


def _release(status=ReleaseStatus.PUBLISHED, **kw) -> PressRelease:
    kw.setdefault("title", "Crosfield opens new plant")
    kw.setdefault("slug", "crosfield-opens-new-plant")
    kw.setdefault("summary", "Lahore-area capacity expansion.")
    kw.setdefault("body", "Full release body.")
    if status == ReleaseStatus.PUBLISHED:
        kw.setdefault("issued_on", timezone.now().date())
    return PressRelease.objects.create(status=status, **kw)


def _coverage(**kw) -> MediaCoverage:
    kw.setdefault("title", "Industry profile: Crosfield")
    kw.setdefault("publication", "Dawn Business")
    kw.setdefault("url", "https://dawn.example/article")
    kw.setdefault("excerpt", "")
    kw.setdefault("published_on", timezone.now().date())
    return MediaCoverage.objects.create(**kw)


class TestIndex:
    def test_renders_with_data(self, client):
        _release(slug="r1", title="R1")
        _coverage(title="C1")
        response = client.get(reverse("media_center:index"))
        assert response.status_code == 200
        assert b"R1" in response.content
        assert b"C1" in response.content

    def test_empty_state(self, client):
        response = client.get(reverse("media_center:index"))
        assert response.status_code == 200
        assert b"No press releases yet" in response.content


class TestPressReleaseDetail:
    def test_404_for_draft(self, client):
        _release(slug="draft", status=ReleaseStatus.DRAFT)
        response = client.get(reverse("media_center:press-detail", kwargs={"slug": "draft"}))
        assert response.status_code == 404

    def test_renders_published_with_jsonld(self, client):
        _release(slug="public", title="Public Release")
        response = client.get(reverse("media_center:press-detail", kwargs={"slug": "public"}))
        assert response.status_code == 200
        assert b"Public Release" in response.content
        assert b'"@type": "NewsArticle"' in response.content


class TestCoverageList:
    def test_lists_active_only(self, client):
        _coverage(title="Active")
        _coverage(title="Inactive", is_active=False)
        response = client.get(reverse("media_center:coverage-list"))
        assert response.status_code == 200
        assert b"Active" in response.content
        assert b"Inactive" not in response.content
