from __future__ import annotations

from django.utils import timezone

import pytest

from apps.products.selectors import (
    get_category_tree,
    get_product_by_slug,
    get_products_for_category,
    get_published_products,
    get_related_products,
    search_products,
)
from apps.products.tests.factories import (
    make_category,
    make_image,
    make_product,
    make_published_product,
)

pytestmark = pytest.mark.django_db


class TestGetPublishedProducts:
    def test_excludes_drafts(self):
        category = make_category()
        make_published_product(category=category, sku="P-1", slug="p-1")
        make_product(category=category, sku="P-2", slug="p-2")  # draft
        assert get_published_products().count() == 1

    def test_excludes_future_published(self):
        category = make_category()
        future = timezone.now() + timezone.timedelta(days=1)
        make_published_product(category=category, sku="P-3", slug="p-3", published_at=future)
        assert get_published_products().count() == 0

    def test_no_n_plus_one_on_images(self, django_assert_num_queries):
        category = make_category()
        for i in range(5):
            p = make_published_product(category=category, sku=f"S-{i}", slug=f"s-{i}")
            make_image(p)
        # 1 SELECT for the product list (category joined via select_related)
        # + 1 SELECT for the images prefetch
        # + 1 SELECT for the variants prefetch
        # = 3 total. (Empty variants result is still a single prefetch query.)
        with django_assert_num_queries(3):
            list(get_published_products())


class TestGetProductBySlug:
    def test_returns_published_only(self):
        category = make_category()
        draft = make_product(category=category, slug="hidden", sku="D-1")
        assert get_product_by_slug(draft.slug) is None

        published = make_published_product(category=category, slug="visible", sku="V-1")
        assert get_product_by_slug(published.slug).pk == published.pk


class TestGetProductsForCategory:
    def test_includes_descendants(self):
        root = make_category(name="Root", slug="root")
        child = make_category(name="Child", slug="child", parent=root)
        grandchild = make_category(name="Grand", slug="grand", parent=child)

        make_published_product(category=root, sku="R-1", slug="r-1")
        make_published_product(category=child, sku="C-1", slug="c-1")
        make_published_product(category=grandchild, sku="G-1", slug="g-1")

        assert get_products_for_category(root).count() == 3
        assert get_products_for_category(child).count() == 2
        assert get_products_for_category(grandchild).count() == 1


class TestGetRelatedProducts:
    def test_returns_same_category_excluding_self(self):
        category = make_category()
        a = make_published_product(category=category, sku="A", slug="a")
        b = make_published_product(category=category, sku="B", slug="b")
        related = list(get_related_products(a))
        assert b in related
        assert a not in related


class TestSearchProducts:
    def test_matches_name(self):
        category = make_category()
        make_published_product(category=category, name="Urea 46", slug="urea-46", sku="UR-46")
        make_published_product(category=category, name="DAP 18", slug="dap-18", sku="DAP-18")
        assert search_products("urea").count() == 1

    def test_matches_sku_exact(self):
        category = make_category()
        make_published_product(category=category, sku="DAP-18", slug="dap", name="DAP")
        assert search_products("DAP-18").count() == 1

    def test_empty_query_returns_empty(self):
        category = make_category()
        make_published_product(category=category, slug="x", sku="X")
        assert search_products("").count() == 0


class TestCategoryTree:
    def test_nests_children_under_parents(self):
        root = make_category(name="Root", slug="root")
        make_category(name="Child", slug="child", parent=root)
        tree = get_category_tree()
        assert len(tree) == 1
        assert tree[0]["slug"] == "root"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["slug"] == "child"
