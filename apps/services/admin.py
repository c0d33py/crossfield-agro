from django.contrib import admin

from apps.services.models import ServiceEnquiry, ServiceOffering


@admin.register(ServiceOffering)
class ServiceOfferingAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "position", "updated_at")
    list_filter = ("is_active", "category")
    list_editable = ("is_active", "position")
    search_fields = ("name", "slug", "summary")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "is_active", "position")}),
        (
            "Content",
            {"fields": ("summary", "body", "deliverables", "typical_timeline", "pricing_model")},
        ),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ServiceEnquiry)
class ServiceEnquiryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "company", "offering", "email")
    list_filter = ("offering",)
    search_fields = ("name", "email", "company", "message")
    raw_id_fields = ("offering",)
    readonly_fields = (
        "offering",
        "name",
        "email",
        "phone",
        "company",
        "message",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Enquiries are created via the public form only.
        return False
