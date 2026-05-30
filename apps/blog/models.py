"""
Editorial blog. Posts have an author (independent of the User model so guest
authors can be credited), one or more tags, and a publish workflow (DRAFT -> PUBLISHED -> ARCHIVED).
"""

from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class PostStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class Author(models.Model):
    """
    Decoupled from auth.User so we can credit guest authors and keep author
    pages independent of internal user accounts.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    role = models.CharField(max_length=140, blank=True, help_text=_('e.g. "Head of Agronomy"'))
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="blog/authors/", null=True, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("blog:author-detail", kwargs={"slug": self.slug})


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("blog:tag-detail", kwargs={"slug": self.slug})


class Post(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, db_index=True)

    author = models.ForeignKey(
        Author,
        related_name="posts",
        on_delete=models.PROTECT,
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    excerpt = models.CharField(
        max_length=300,
        help_text=_("One-line summary for cards and meta description fallback."),
    )
    body = models.TextField(help_text=_("Markdown or HTML — rendered as-is via |safe."))

    hero_image = models.ImageField(upload_to="blog/%Y/%m/", null=True, blank=True)
    hero_alt = models.CharField(max_length=200, blank=True)

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    status = models.CharField(
        max_length=16,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["author", "-published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("blog:post-detail", kwargs={"slug": self.slug})

    @property
    def is_published(self) -> bool:
        return (
            self.status == PostStatus.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )
