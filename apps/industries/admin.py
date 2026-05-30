from django.contrib import admin

from apps.industries.models import Industry


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "position", "updated_at")
    list_filter = ("is_active",)
    list_editable = ("is_active", "position")
    search_fields = ("name", "slug", "summary")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active", "position")}),
        ("Content", {"fields": ("summary", "body", "hero_image", "icon")}),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
