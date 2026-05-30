from django.contrib import admin

from apps.cart.models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("product", "variant")
    fields = ("product", "variant", "quantity", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "session_key")
    raw_id_fields = ("user",)
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "variant", "quantity", "updated_at")
    raw_id_fields = ("cart", "product", "variant")
    search_fields = ("product__name", "product__sku")
