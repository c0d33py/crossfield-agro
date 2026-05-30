"""
Industry landing pages — one per market segment we serve. Linked M:N to Product
via products.Product.industries (declared on the Product side).
"""

from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Industry(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)

    summary = models.CharField(
        max_length=300,
        help_text=_("One-line summary used in cards and meta description fallback."),
    )
    body = models.TextField(
        blank=True,
        help_text=_("Long-form description rendered on the industry detail page."),
    )

    hero_image = models.ImageField(upload_to="industries/%Y/", null=True, blank=True)
    icon = models.CharField(
        max_length=40,
        blank=True,
        help_text=_("Short label key (e.g. 'wheat') for icon selection in templates."),
    )

    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0, db_index=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "industries"
        ordering = ["position", "name"]
        indexes = [models.Index(fields=["is_active", "position"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("industries:detail", kwargs={"slug": self.slug})
