from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from apps.products.models import ProductStatus
from apps.products.services import (
    archive_product,
    create_product,
    create_variant,
    publish_product,
    update_product,
)
from apps.products.tests.factories import make_category, make_image, make_product

pytestmark = pytest.mark.django_db


class TestCreateProduct:
    def test_creates_in_draft_status(self):
        category = make_category()
        product = create_product(
            name="Urea 46%",
            sku="UR-46",
            category=category,
            unit_price=Decimal("2500.00"),
        )
        assert product.status == ProductStatus.DRAFT
        assert product.slug == "urea-46"

    def test_rejects_negative_price(self):
        category = make_category()
        with pytest.raises(ValidationError):
            create_product(name="Bad", sku="BAD-1", category=category, unit_price=Decimal("-1.00"))

    def test_rejects_empty_sku(self):
        category = make_category()
        with pytest.raises(ValidationError):
            create_product(name="Bad", sku="", category=category, unit_price=Decimal("10.00"))

    def test_rejects_max_qty_below_min(self):
        category = make_category()
        with pytest.raises(ValidationError):
            create_product(
                name="Bad",
                sku="BAD-2",
                category=category,
                unit_price=Decimal("10.00"),
                min_order_quantity=10,
                max_order_quantity=5,
            )

    def test_slug_is_unique(self):
        category = make_category()
        create_product(name="Same Name", sku="A-1", category=category, unit_price=Decimal("1.00"))
        second = create_product(
            name="Same Name", sku="A-2", category=category, unit_price=Decimal("1.00")
        )
        assert second.slug == "same-name-2"


class TestUpdateProduct:
    def test_updates_allowed_fields(self):
        product = make_product()
        updated = update_product(product=product, unit_price=Decimal("9999.00"))
        assert updated.unit_price == Decimal("9999.00")

    def test_rejects_invalid_price_update(self):
        product = make_product()
        with pytest.raises(ValidationError):
            update_product(product=product, unit_price=Decimal("-5.00"))


class TestPublishProduct:
    def test_requires_at_least_one_image(self):
        product = make_product()
        with pytest.raises(ValidationError):
            publish_product(product=product)

    def test_publishes_with_image(self):
        product = make_product()
        make_image(product)
        published = publish_product(product=product)
        assert published.status == ProductStatus.PUBLISHED
        assert published.published_at is not None


class TestArchiveProduct:
    def test_sets_status_archived(self):
        product = make_product()
        archived = archive_product(product=product)
        assert archived.status == ProductStatus.ARCHIVED


class TestVariants:
    def test_creates_variant(self):
        product = make_product()
        variant = create_variant(
            product=product,
            name="100kg",
            sku="UR-46-100",
            unit_price=Decimal("4800.00"),
            stock_quantity=20,
        )
        assert variant.product_id == product.pk
        assert variant.is_active is True

    def test_variant_rejects_negative_price(self):
        product = make_product()
        with pytest.raises(ValidationError):
            create_variant(
                product=product,
                name="Bad",
                sku="UR-46-BAD",
                unit_price=Decimal("-1.00"),
            )
