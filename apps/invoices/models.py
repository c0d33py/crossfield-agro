"""
Invoices: sequential, immutable per fiscal year. Numbers never reused.

The InvoiceSequence row is select_for_update'd during number issuance to
serialise allocation across concurrent workers.
"""

from __future__ import annotations

from django.db import models


class InvoiceSequence(models.Model):
    fiscal_year = models.PositiveIntegerField(unique=True, db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Invoice number sequence"

    def __str__(self) -> str:
        return f"FY{self.fiscal_year}: {self.last_number}"


class Invoice(models.Model):
    order = models.OneToOneField("orders.Order", related_name="invoice", on_delete=models.PROTECT)
    number = models.CharField(max_length=32, unique=True, db_index=True)
    fiscal_year = models.PositiveIntegerField(db_index=True)

    pdf = models.FileField(upload_to="invoices/%Y/", null=True, blank=True)

    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.number

    @property
    def is_paid(self) -> bool:
        """Derived from payment status — invoices issued at CONFIRMED start unpaid."""
        from apps.payments.models import PaymentStatus

        return self.order.payments.filter(status=PaymentStatus.SUCCEEDED).exists()

    @property
    def document_type(self) -> str:
        """'Tax Invoice' once paid, 'Proforma Invoice' beforehand."""
        return "Tax Invoice" if self.is_paid else "Proforma Invoice"
