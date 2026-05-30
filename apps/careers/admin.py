from django.contrib import admin

from apps.careers.models import Department, JobApplication, JobPosting


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "position")
    list_filter = ("is_active",)
    list_editable = ("is_active", "position")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "department",
        "location",
        "employment_type",
        "status",
        "published_at",
        "closes_at",
    )
    list_filter = ("status", "department", "employment_type", "experience_level")
    search_fields = ("title", "summary", "description")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("department",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "slug",
                    "department",
                    "location",
                    "employment_type",
                    "experience_level",
                    "status",
                    "published_at",
                    "closes_at",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "summary",
                    "description",
                    "responsibilities",
                    "requirements",
                    "benefits",
                )
            },
        ),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "full_name",
        "posting",
        "status",
        "email",
        "location",
    )
    list_filter = ("status", "posting__department", "posting")
    search_fields = ("full_name", "email", "phone", "location", "cover_letter")
    list_editable = ("status",)
    readonly_fields = (
        "posting",
        "full_name",
        "email",
        "phone",
        "location",
        "cv",
        "cover_letter",
        "linkedin_url",
        "submitter_ip",
        "user_agent",
        "created_at",
    )
    raw_id_fields = ("posting",)
    fieldsets = (
        (
            "Application",
            {
                "fields": (
                    "posting",
                    "full_name",
                    "email",
                    "phone",
                    "location",
                    "cv",
                    "cover_letter",
                    "linkedin_url",
                    "created_at",
                )
            },
        ),
        ("Audit", {"fields": ("submitter_ip", "user_agent"), "classes": ("collapse",)}),
        ("Workflow", {"fields": ("status", "internal_notes")}),
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False
