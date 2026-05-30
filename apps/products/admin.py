from django.contrib import admin
from django.utils.html import format_html

from apps.products.models import Category, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "thumbnail", "alt_text", "position", "is_primary")
    readonly_fields = ("thumbnail",)

    def thumbnail(self, obj: ProductImage) -> str:
        if not obj.pk or not obj.image:
            return ""
        return format_html(
            '<img src="{}" style="height: 60px; border-radius: 4px;" />', obj.image.url
        )


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("name", "sku", "unit_price", "stock_quantity", "is_active", "position")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "position", "updated_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("parent",)
    list_editable = ("is_active", "position")
    ordering = ("position", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "unit_price",
        "currency",
        "status",
        "stock_quantity",
        "published_at",
        "updated_at",
    )
    list_filter = ("status", "category", "track_inventory", "allow_backorder", "currency")
    search_fields = ("name", "sku", "slug", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("category", "created_by")
    readonly_fields = ("created_at", "updated_at", "published_at")
    list_select_related = ("category",)
    date_hierarchy = "created_at"
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "category", "status")}),
        ("Content", {"fields": ("short_description", "description", "specifications")}),
        ("Pricing", {"fields": ("unit_price", "currency")}),
        (
            "Inventory",
            {
                "fields": (
                    "track_inventory",
                    "stock_quantity",
                    "allow_backorder",
                    "low_stock_threshold",
                )
            },
        ),
        (
            "Order constraints",
            {"fields": ("min_order_quantity", "max_order_quantity", "weight_kg")},
        ),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        (
            "Audit",
            {"fields": ("created_by", "created_at", "updated_at", "published_at")},
        ),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "position", "is_primary", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("product__name", "alt_text")
    raw_id_fields = ("product",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "name",
        "sku",
        "unit_price",
        "stock_quantity",
        "is_active",
        "position",
    )
    list_filter = ("is_active",)
    search_fields = ("product__name", "sku", "name")
    raw_id_fields = ("product",)
    list_editable = ("is_active", "position")
