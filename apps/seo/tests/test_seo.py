from __future__ import annotations

from django.urls import reverse

import pytest

from apps.seo.models import PageMetadata, Redirect, RobotsRule

pytestmark = pytest.mark.django_db


class TestPageMetadataOverride:
    def test_title_and_description_override(self, client):
        PageMetadata.objects.create(
            path="/",
            title="Custom Title — Crosfield",
            description="Admin-set description for the home page.",
        )
        response = client.get("/")
        assert response.status_code == 200
        assert b"Custom Title \xe2\x80\x94 Crosfield" in response.content
        assert b"Admin-set description for the home page." in response.content

    def test_noindex_emits_robots_meta(self, client):
        PageMetadata.objects.create(path="/", noindex=True)
        response = client.get("/")
        assert b'<meta name="robots" content="noindex,follow">' in response.content

    def test_canonical_override(self, client):
        PageMetadata.objects.create(path="/", canonical_url="https://crosfieldagro.com.pk/")
        response = client.get("/")
        assert b'<link rel="canonical" href="https://crosfieldagro.com.pk/">' in response.content


class TestRedirectMiddleware:
    def test_active_redirect_301(self, client):
        Redirect.objects.create(
            source_path="/old-page/",
            target_url="/products/",
            status_code=301,
        )
        response = client.get("/old-page/")
        assert response.status_code == 301
        assert response.url == "/products/"

    def test_inactive_redirect_passes_through(self, client):
        Redirect.objects.create(
            source_path="/dead/",
            target_url="/products/",
            status_code=301,
            is_active=False,
        )
        response = client.get("/dead/")
        # The slug-catch-all in core will return 404
        assert response.status_code == 404


class TestRobotsTxt:
    def test_default_when_no_rules(self, client):
        response = client.get(reverse("robots-txt"))
        assert response.status_code == 200
        body = response.content.decode()
        assert "User-agent: *" in body
        assert "Disallow: /admin/" in body
        assert "Sitemap:" in body

    def test_uses_db_rules_when_present(self, client):
        RobotsRule.objects.create(directive="user_agent", value="*", position=1)
        RobotsRule.objects.create(directive="disallow", value="/private/", position=2)
        response = client.get(reverse("robots-txt"))
        body = response.content.decode()
        assert "User-agent: *" in body
        assert "Disallow: /private/" in body
        # The default Disallow: /admin/ should NOT appear (DB rules take over)
        assert "Disallow: /admin/" not in body
