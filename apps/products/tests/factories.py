from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.products.models import Category, Product, ProductImage, ProductStatus, ProductVariant


def make_category(**overrides) -> Category:
    defaults = {"name": "Fertilizers", "slug": "fertilizers", "is_active": True}
    defaults.update(overrides)
    return Category.objects.create(**defaults)


def make_product(category: Category | None = None, **overrides) -> Product:
    if category is None:
        category = make_category()
    defaults = {
        "name": "Nitrogen Fertilizer",
        "slug": "nitrogen-fertilizer",
        "sku": "NF-001",
        "category": category,
        "unit_price": Decimal("1500.00"),
        "stock_quantity": 100,
        "status": ProductStatus.DRAFT,
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


def make_published_product(category: Category | None = None, **overrides) -> Product:
    overrides.setdefault("status", ProductStatus.PUBLISHED)
    overrides.setdefault("published_at", timezone.now())
    return make_product(category=category, **overrides)


def make_variant(product: Product, **overrides) -> ProductVariant:
    defaults = {
        "name": "50kg bag",
        "sku": f"{product.sku}-50KG",
        "unit_price": Decimal("1500.00"),
        "stock_quantity": 50,
    }
    defaults.update(overrides)
    return ProductVariant.objects.create(product=product, **defaults)


def make_image(product: Product, **overrides) -> ProductImage:
    from django.core.files.uploadedfile import SimpleUploadedFile

    image_file = SimpleUploadedFile("test.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
    defaults = {"image": image_file, "alt_text": "test image", "position": 0}
    defaults.update(overrides)
    return ProductImage.objects.create(product=product, **defaults)
