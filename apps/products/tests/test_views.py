from __future__ import annotations

from django.urls import reverse

import pytest

from apps.products.tests.factories import make_category, make_image, make_published_product

pytestmark = pytest.mark.django_db


class TestProductListView:
    def test_renders_published_products(self, client):
        category = make_category()
        product = make_published_product(category=category, name="Urea")
        response = client.get(reverse("products:product-list"))
        assert response.status_code == 200
        assert product.name.encode() in response.content


class TestProductDetailView:
    def test_404_for_unknown_slug(self, client):
        response = client.get(reverse("products:product-detail", kwargs={"slug": "no-such-thing"}))
        assert response.status_code == 404

    def test_404_for_draft_product(self, client):
        from apps.products.tests.factories import make_product

        category = make_category()
        draft = make_product(category=category, slug="draft", sku="DR-1")
        response = client.get(reverse("products:product-detail", kwargs={"slug": draft.slug}))
        assert response.status_code == 404

    def test_renders_json_ld_for_published(self, client):
        category = make_category()
        product = make_published_product(category=category, slug="visible", sku="V-1")
        make_image(product)
        response = client.get(reverse("products:product-detail", kwargs={"slug": product.slug}))
        assert response.status_code == 200
        assert b'"@type": "Product"' in response.content
        assert b'"@type": "Offer"' in response.content


class TestCategoryDetailView:
    def test_renders_category_with_products(self, client):
        category = make_category(name="Fertilizers", slug="fertilizers")
        make_published_product(category=category, name="Urea", slug="urea", sku="U-1")
        response = client.get(reverse("products:category-detail", kwargs={"slug": category.slug}))
        assert response.status_code == 200
        assert b"Urea" in response.content
        assert b'"@type": "CollectionPage"' in response.content


class TestProductSearchView:
    def test_search_finds_matching(self, client):
        category = make_category()
        make_published_product(category=category, name="Urea 46", slug="urea-46", sku="U-46")
        make_published_product(category=category, name="DAP 18", slug="dap-18", sku="D-18")
        response = client.get(reverse("products:product-search"), {"q": "urea"})
        assert response.status_code == 200
        assert b"Urea 46" in response.content
        assert b"DAP 18" not in response.content

    def test_search_is_noindex(self, client):
        response = client.get(reverse("products:product-search"))
        assert b'name="robots"' in response.content
        assert b"noindex" in response.content
