"""
ContactMessage — persistent record of every enquiry submitted via the contact form.

Immutable from the public side; only staff (via admin) can mark resolved or
add internal notes. Replaces the in-memory stub previously living in apps/core.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class EnquiryType(models.TextChoices):
    SALES = "sales", _("Sales / Quote")
    TECHNICAL = "technical", _("Technical Support")
    PARTNERSHIP = "partnership", _("Partnership")
    CAREERS = "careers", _("Careers")
    MEDIA = "media", _("Media / Press")
    OTHER = "other", _("Other")


class ContactStatus(models.TextChoices):
    NEW = "new", _("New")
    IN_PROGRESS = "in_progress", _("In Progress")
    RESPONDED = "responded", _("Responded")
    CLOSED = "closed", _("Closed")
    SPAM = "spam", _("Spam / Discarded")


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=140, blank=True)
    enquiry_type = models.CharField(max_length=24, choices=EnquiryType.choices, db_index=True)
    message = models.TextField()

    # Staff-only fields
    status = models.CharField(
        max_length=24,
        choices=ContactStatus.choices,
        default=ContactStatus.NEW,
        db_index=True,
    )
    internal_notes = models.TextField(
        blank=True,
        help_text=_("Staff notes. Never shown to the customer."),
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    # Audit
    submitter_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["enquiry_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_enquiry_type_display()}) — {self.created_at:%Y-%m-%d}"
