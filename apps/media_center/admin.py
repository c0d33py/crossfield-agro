from django.contrib import admin

from apps.media_center.models import MediaCoverage, PressRelease


@admin.register(PressRelease)
class PressReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "issued_on", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "issued_on"
    fieldsets = (
        (None, {"fields": ("title", "slug", "status", "issued_on")}),
        ("Content", {"fields": ("summary", "body", "hero_image", "pdf")}),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(MediaCoverage)
class MediaCoverageAdmin(admin.ModelAdmin):
    list_display = ("title", "publication", "published_on", "is_featured", "is_active")
    list_filter = ("is_featured", "is_active", "publication")
    list_editable = ("is_featured", "is_active")
    search_fields = ("title", "publication", "excerpt", "url")
    date_hierarchy = "published_on"
