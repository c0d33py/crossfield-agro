from django.contrib import admin

from apps.blog.models import Author, Post, Tag


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "role", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "role")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "updated_at")
    list_filter = ("status", "author", "tags")
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "tags", "status", "published_at")}),
        ("Content", {"fields": ("excerpt", "body", "hero_image", "hero_alt")}),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
