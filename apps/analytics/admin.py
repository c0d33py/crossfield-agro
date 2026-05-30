from django.contrib import admin

from apps.analytics.models import DailyRollup, Event, PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("created_at", "path", "user", "ip_prefix")
    list_filter = ("created_at",)
    search_fields = ("path", "session_key", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in PageView._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "path", "user")
    list_filter = ("name", "created_at")
    search_fields = ("name", "path", "session_key", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in Event._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DailyRollup)
class DailyRollupAdmin(admin.ModelAdmin):
    list_display = ("date", "path", "views", "unique_sessions", "events")
    list_filter = ("date",)
    search_fields = ("path",)
    date_hierarchy = "date"
    readonly_fields = (
        "date",
        "path",
        "views",
        "unique_sessions",
        "events",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
