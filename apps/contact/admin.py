from django.contrib import admin

from apps.contact.models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "name",
        "company",
        "enquiry_type",
        "status",
        "email",
    )
    list_filter = ("status", "enquiry_type", "created_at")
    search_fields = ("name", "email", "company", "message")
    list_editable = ("status",)
    readonly_fields = (
        "name",
        "email",
        "phone",
        "company",
        "enquiry_type",
        "message",
        "submitter_ip",
        "user_agent",
        "created_at",
    )
    fieldsets = (
        (
            "Submission",
            {
                "fields": (
                    "name",
                    "email",
                    "phone",
                    "company",
                    "enquiry_type",
                    "message",
                    "created_at",
                )
            },
        ),
        ("Audit", {"fields": ("submitter_ip", "user_agent"), "classes": ("collapse",)}),
        ("Staff workflow", {"fields": ("status", "internal_notes", "responded_at")}),
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Messages are created via the public form only.
        return False
