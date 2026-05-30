from django.contrib import admin

from apps.audit.models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "actor_label",
        "target_type",
        "target_label",
        "ip_address",
    )
    list_filter = ("action", "target_type", "created_at")
    search_fields = (
        "actor_label",
        "target_label",
        "target_id",
        "description",
        "ip_address",
    )
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in AuditLogEntry._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow superusers only — for ops to truncate old rows
        return request.user.is_superuser
