"""
Media Center — PressRelease (issued by us) and MediaCoverage (external mentions).
"""

from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ReleaseStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class PressRelease(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, db_index=True)

    summary = models.CharField(max_length=300)
    body = models.TextField()

    hero_image = models.ImageField(upload_to="media/press/%Y/", null=True, blank=True)
    pdf = models.FileField(
        upload_to="media/press/pdf/%Y/",
        null=True,
        blank=True,
        help_text=_("Optional downloadable PDF version of the release."),
    )

    status = models.CharField(
        max_length=16,
        choices=ReleaseStatus.choices,
        default=ReleaseStatus.DRAFT,
        db_index=True,
    )
    issued_on = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Date of release. Displayed publicly. Distinct from created_at."),
    )

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_on", "-created_at"]
        indexes = [models.Index(fields=["status", "-issued_on"])]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("media_center:press-detail", kwargs={"slug": self.slug})


class MediaCoverage(models.Model):
    """An external article or interview that mentions Crosfield."""

    title = models.CharField(max_length=300)
    publication = models.CharField(max_length=200, help_text=_('e.g. "Dawn Business"'))
    url = models.URLField()
    excerpt = models.CharField(max_length=400, blank=True)

    published_on = models.DateField(db_index=True)

    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Media coverage"
        verbose_name_plural = "Media coverage"
        ordering = ["-published_on"]
        indexes = [
            models.Index(fields=["is_active", "-published_on"]),
            models.Index(fields=["is_featured", "-published_on"]),
        ]

    def __str__(self) -> str:
        return f"{self.publication}: {self.title}"
