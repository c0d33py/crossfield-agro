from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ProductStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    parent = models.ForeignKey(
        "self",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    description = models.TextField(blank=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["position", "name"]
        indexes = [
            models.Index(fields=["is_active", "position"]),
            models.Index(fields=["parent", "position"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("products:category-detail", kwargs={"slug": self.slug})


class Product(models.Model):
    """
    Product is the catalog row. Its `unit_price` is the **current** price —
    orders snapshot this value at creation time (see apps/orders).

    Stock-keeping fields (`stock_quantity`, `track_inventory`) are the
    authoritative source. Decrement happens on order PAID transition via
    the orders service, never from here.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    sku = models.CharField(max_length=64, unique=True, db_index=True)

    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
    )

    industries = models.ManyToManyField(
        "industries.Industry",
        related_name="products",
        blank=True,
        help_text=_("Market segments this product serves; powers industry landing pages."),
    )

    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Current price. Snapshotted onto OrderItem at order creation."),
    )
    currency = models.CharField(max_length=3, default="PKR")

    track_inventory = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    allow_backorder = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    min_order_quantity = models.PositiveIntegerField(default=1)
    max_order_quantity = models.PositiveIntegerField(null=True, blank=True)

    weight_kg = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="products_created",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name="product_unit_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(min_order_quantity__gte=1),
                name="product_min_order_quantity_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    def get_absolute_url(self) -> str:
        return reverse("products:product-detail", kwargs={"slug": self.slug})

    @property
    def is_published(self) -> bool:
        return (
            self.status == ProductStatus.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    @property
    def is_in_stock(self) -> bool:
        if not self.track_inventory:
            return True
        if self.allow_backorder:
            return True
        return self.stock_quantity > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Descriptive alt text — required for accessibility and SEO."),
    )
    position = models.PositiveIntegerField(default=0, db_index=True)
    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["product", "position"])]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="product_one_primary_image",
            ),
        ]

    def __str__(self) -> str:
        return f"Image for {self.product_id} ({self.position})"


class ProductVariant(models.Model):
    """
    Optional variant (e.g. pack size). When present, the variant's price
    and stock override the parent product's at order time. Snapshotted
    on OrderItem just like the parent product.
    """

    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, unique=True, db_index=True)

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    stock_quantity = models.PositiveIntegerField(default=0)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('e.g. {"size": "50kg", "grade": "industrial"}'),
    )

    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name="variant_unit_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name}"
