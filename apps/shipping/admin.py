from django.contrib import admin

from apps.shipping.models import ShippingMethod, ShippingRate


class ShippingRateInline(admin.TabularInline):
    model = ShippingRate
    extra = 0


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "position")
    list_filter = ("is_active",)
    list_editable = ("is_active", "position")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}
    inlines = [ShippingRateInline]


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ("method", "country", "min_weight_kg", "max_weight_kg", "price", "currency")
    list_filter = ("country", "currency", "method")
