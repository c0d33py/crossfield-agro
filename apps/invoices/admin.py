from django.contrib import admin

from apps.invoices.models import Invoice, InvoiceSequence


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "fiscal_year", "issued_at")
    list_filter = ("fiscal_year",)
    search_fields = ("number", "order__number")
    raw_id_fields = ("order",)
    readonly_fields = ("number", "fiscal_year", "issued_at", "order")


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("fiscal_year", "last_number")
    readonly_fields = ("fiscal_year", "last_number")

    # No add/delete — these are managed by allocate_invoice_number()
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
