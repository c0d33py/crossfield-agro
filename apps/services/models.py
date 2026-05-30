"""
Service offerings — what Crosfield does beyond shipping product
(agronomy support, contract manufacturing, formulation development, logistics).

A ServiceEnquiry is the record of a customer expressing interest in a service.
Enquiries are immutable — status changes go into ServiceEnquiryEvent if/when
that scope grows. For now we only need create + admin read.
"""

from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ServiceCategory(models.TextChoices):
    AGRONOMY = "agronomy", _("Agronomy support")
    MANUFACTURING = "manufacturing", _("Contract manufacturing")
    FORMULATION = "formulation", _("Formulation development")
    LOGISTICS = "logistics", _("Logistics & supply")
    OTHER = "other", _("Other")


class ServiceOffering(models.Model):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, db_index=True)
    category = models.CharField(max_length=24, choices=ServiceCategory.choices, db_index=True)

    summary = models.CharField(max_length=300)
    body = models.TextField(blank=True, help_text=_("Long-form description."))
    deliverables = models.JSONField(
        default=list,
        blank=True,
        help_text=_(
            'List of deliverables, e.g. ["Field visit", "Soil sampling", "Written report"].'
        ),
    )
    typical_timeline = models.CharField(max_length=120, blank=True, help_text=_('e.g. "4–6 weeks"'))
    pricing_model = models.CharField(
        max_length=140,
        blank=True,
        help_text=_('e.g. "Fixed scope" or "Time & materials".'),
    )

    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0, db_index=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        indexes = [
            models.Index(fields=["is_active", "position"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("services:detail", kwargs={"slug": self.slug})


class ServiceEnquiry(models.Model):
    """Immutable record of an enquiry against a specific service offering."""

    offering = models.ForeignKey(
        ServiceOffering,
        related_name="enquiries",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=_(
            "Service the customer is enquiring about. Optional — may be a general services enquiry."
        ),
    )

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=140, blank=True)
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["offering", "-created_at"])]

    def __str__(self) -> str:
        return f"Enquiry from {self.name} ({self.created_at:%Y-%m-%d})"
