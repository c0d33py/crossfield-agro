from __future__ import annotations

from django.urls import reverse

import pytest

from apps.industries.models import Industry
from apps.industries.selectors import (
    get_active_industries,
    get_industry_by_slug,
    get_products_for_industry,
)
from apps.products.tests.factories import make_product, make_published_product

pytestmark = pytest.mark.django_db


def _ind(**kw) -> Industry:
    kw.setdefault("name", "Cereals")
    kw.setdefault("slug", "cereals")
    kw.setdefault("summary", "Wheat, rice, maize.")
    return Industry.objects.create(**kw)


class TestSelectors:
    def test_get_active_industries_excludes_inactive(self):
        _ind(name="Active", slug="a")
        _ind(name="Inactive", slug="b", is_active=False)
        assert list(get_active_industries().values_list("slug", flat=True)) == ["a"]

    def test_get_industry_by_slug_404s_on_inactive(self):
        _ind(name="Hidden", slug="hidden", is_active=False)
        assert get_industry_by_slug("hidden") is None

    def test_get_products_for_industry_only_published(self):
        from apps.products.tests.factories import make_category

        industry = _ind()
        category = make_category()
        published = make_published_product(category=category, name="P1", slug="p1", sku="P1")
        draft = make_product(category=category, name="P2", slug="p2", sku="P2")
        published.industries.add(industry)
        draft.industries.add(industry)

        slugs = list(get_products_for_industry(industry).values_list("slug", flat=True))
        assert "p1" in slugs
        assert "p2" not in slugs


class TestIndustryListView:
    def test_renders_industries(self, client):
        _ind(name="Cotton", slug="cotton")
        response = client.get(reverse("industries:list"))
        assert response.status_code == 200
        assert b"Cotton" in response.content

    def test_omits_inactive(self, client):
        _ind(name="Hidden", slug="hidden", is_active=False)
        response = client.get(reverse("industries:list"))
        assert b"Hidden" not in response.content


class TestIndustryDetailView:
    def test_404_for_unknown_slug(self, client):
        response = client.get(reverse("industries:detail", kwargs={"slug": "no"}))
        assert response.status_code == 404

    def test_404_for_inactive(self, client):
        _ind(slug="hidden", is_active=False)
        response = client.get(reverse("industries:detail", kwargs={"slug": "hidden"}))
        assert response.status_code == 404

    def test_renders_with_products(self, client):
        industry = _ind(slug="horticulture", name="Horticulture")
        product = make_published_product(name="Foliar Mix", slug="foliar-mix", sku="FM-1")
        product.industries.add(industry)

        response = client.get(reverse("industries:detail", kwargs={"slug": "horticulture"}))
        assert response.status_code == 200
        assert b"Horticulture" in response.content
        assert b"Foliar Mix" in response.content
        assert b'"@type": "CollectionPage"' in response.content
        assert b'"@type": "BreadcrumbList"' in response.content

    def test_renders_empty_state(self, client):
        _ind(slug="new-segment", name="New Segment")
        response = client.get(reverse("industries:detail", kwargs={"slug": "new-segment"}))
        assert response.status_code == 200
        assert b"Products are being added" in response.content
