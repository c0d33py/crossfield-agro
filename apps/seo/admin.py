from django.contrib import admin

from apps.seo.models import PageMetadata, Redirect, RobotsRule


@admin.register(PageMetadata)
class PageMetadataAdmin(admin.ModelAdmin):
    list_display = ("path", "title", "noindex", "updated_at")
    list_filter = ("noindex", "nofollow")
    search_fields = ("path", "title", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("path", "notes")}),
        ("Title & description", {"fields": ("title", "description", "canonical_url")}),
        ("Open Graph", {"fields": ("og_title", "og_description", "og_image")}),
        ("Indexing", {"fields": ("noindex", "nofollow")}),
        ("Structured data", {"fields": ("extra_json_ld",)}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("source_path", "target_url", "status_code", "is_active", "hits", "updated_at")
    list_filter = ("status_code", "is_active")
    list_editable = ("is_active",)
    search_fields = ("source_path", "target_url", "notes")
    readonly_fields = ("hits", "created_at", "updated_at")


@admin.register(RobotsRule)
class RobotsRuleAdmin(admin.ModelAdmin):
    list_display = ("directive", "value", "position", "is_active")
    list_filter = ("directive", "is_active")
    list_editable = ("position", "is_active")
    search_fields = ("value",)
    ordering = ("position",)
