"""SEO coverage tests — JSON-LD, sitemap, OG/Twitter tags."""

from __future__ import annotations

import json
import re

from django.urls import reverse

import pytest

pytestmark = pytest.mark.django_db


def _extract_json_ld(html: bytes) -> list[dict]:
    """Pull out every <script type="application/ld+json"> block as parsed JSON."""
    matches = re.findall(
        rb'<script type="application/ld\+json">\s*(.+?)\s*</script>',
        html,
        re.DOTALL,
    )
    return [json.loads(m.decode()) for m in matches]


class TestHomepageStructuredData:
    def test_emits_organization_and_website_schemas(self, client):
        response = client.get(reverse("core:home"))
        assert response.status_code == 200
        ld_blocks = _extract_json_ld(response.content)
        types = {b.get("@type") for b in ld_blocks}
        assert "Organization" in types
        assert "WebSite" in types

    def test_organization_has_required_fields(self, client):
        response = client.get(reverse("core:home"))
        org = next(
            b for b in _extract_json_ld(response.content) if b.get("@type") == "Organization"
        )
        assert org["name"] == "Crosfield Agro"
        assert "logo" in org
        assert "sameAs" in org and len(org["sameAs"]) >= 4  # 4 social profiles
        assert "contactPoint" in org

    def test_website_has_search_action(self, client):
        response = client.get(reverse("core:home"))
        site = next(b for b in _extract_json_ld(response.content) if b.get("@type") == "WebSite")
        assert site["potentialAction"]["@type"] == "SearchAction"
        assert "{search_term_string}" in site["potentialAction"]["target"]


class TestCorporatePagesStructuredData:
    """Every page extending core/_page.html must emit WebPage + BreadcrumbList."""

    @pytest.mark.parametrize(
        "slug",
        [
            "about-us",
            "company-overview",
            "our-history",
            "mission-vision",
            "leadership-team",
            "message-from-ceo",
            "global-presence",
            "privacy-policy",
            "terms-conditions",
            "faq",
        ],
    )
    def test_page_emits_webpage_and_breadcrumb(self, client, slug):
        response = client.get(reverse("core:page", kwargs={"slug": slug}))
        if response.status_code == 404:
            pytest.skip(f"page template for {slug!r} not published")
        assert response.status_code == 200
        ld_blocks = _extract_json_ld(response.content)
        webpage = next((b for b in ld_blocks if b.get("@type") == "WebPage"), None)
        assert webpage is not None, f"missing WebPage JSON-LD on /{slug}/"
        assert "breadcrumb" in webpage
        assert webpage["breadcrumb"]["@type"] == "BreadcrumbList"

    def test_faq_page_preserves_its_own_jsonld(self, client):
        """Regression: FAQ has FAQPage JSON-LD; _page.html shouldn't clobber it."""
        response = client.get(reverse("core:page", kwargs={"slug": "faq"}))
        if response.status_code == 404:
            pytest.skip("faq template not published")
        types = {b.get("@type") for b in _extract_json_ld(response.content)}
        assert "FAQPage" in types
        assert "WebPage" in types  # both must coexist via {{ block.super }}


class TestOpenGraphAndTwitter:
    def test_homepage_sets_full_og_set(self, client):
        response = client.get(reverse("core:home"))
        content = response.content
        assert b'property="og:type"' in content
        assert b'property="og:site_name"' in content
        assert b'property="og:url"' in content
        assert b'property="og:title"' in content
        assert b'property="og:description"' in content
        assert b'property="og:image"' in content  # falls back to default

    def test_homepage_sets_twitter_tags(self, client):
        """Regression: twitter:card declared summary_large_image but no image."""
        response = client.get(reverse("core:home"))
        content = response.content
        assert b'name="twitter:card"' in content
        assert b'name="twitter:title"' in content
        assert b'name="twitter:description"' in content
        assert b'name="twitter:image"' in content


class TestSitemapCoverage:
    def test_sitemap_includes_home(self, client):
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        # Homepage URL should appear exactly once.
        assert response.content.count(b"<loc>https://testserver/</loc>") == 1

    def test_sitemap_includes_corporate_pages(self, client):
        """Regression: 25 corporate pages were invisible to sitemap until apps.core.sitemaps existed."""
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        # Spot-check a handful of slugs we know exist
        for slug in ("about-us", "company-overview", "global-presence", "privacy-policy"):
            assert f"/{slug}/".encode() in response.content, f"slug {slug!r} missing from sitemap"
