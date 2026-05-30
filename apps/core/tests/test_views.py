from __future__ import annotations

from django.urls import reverse

import pytest

from apps.core.selectors import get_all_pages


@pytest.mark.django_db
class TestHomeView:
    def test_renders(self, client):
        response = client.get(reverse("core:home"))
        assert response.status_code == 200
        assert b"Crosfield" in response.content
        # Org JSON-LD on home
        assert b'"@type": "Organization"' in response.content


@pytest.mark.django_db
class TestPageDispatcher:
    def test_404_for_unknown_slug(self, client):
        response = client.get(reverse("core:page", kwargs={"slug": "no-such-page"}))
        assert response.status_code == 404

    @pytest.mark.parametrize("page", [p for p in get_all_pages()])
    def test_every_registered_page_renders(self, client, page):
        from django.utils.html import escape

        response = client.get(reverse("core:page", kwargs={"slug": page.slug}))
        assert response.status_code == 200, f"{page.slug} returned {response.status_code}"
        # Each page must surface its title (HTML-escaped) and an SEO meta description
        assert (
            escape(page.title).encode() in response.content
        ), f"{page.slug}: title {page.title!r} not in body"
        assert b'name="description"' in response.content


# NOTE: TestContactForm moved to apps/contact/tests/test_contact.py.
# /contact-us/ is now served by apps.contact (not a core page).


@pytest.mark.django_db
class TestSiteMap:
    def test_lists_every_registered_page(self, client):
        from django.utils.html import escape

        response = client.get(reverse("core:page", kwargs={"slug": "site-map"}))
        assert response.status_code == 200
        for page in get_all_pages():
            assert escape(page.title).encode() in response.content, f"missing: {page.slug}"


@pytest.mark.django_db
class TestHeaderNav:
    def test_header_renders_primary_nav(self, client):
        response = client.get(reverse("core:home"))
        assert b'aria-label="Primary"' in response.content
        assert b"About" in response.content
        assert b"Products" in response.content
        assert b"Contact" in response.content

    def test_footer_renders_legal_links(self, client):
        response = client.get(reverse("core:home"))
        for slug in ("privacy-policy", "terms-conditions", "cookie-policy", "disclaimer"):
            assert slug.encode() in response.content, f"footer missing {slug}"
