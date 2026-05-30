"""
SEO app — centralized metadata, redirects, and robots rules.

Per .claude/rules/seo.md: "The seo app owns all metadata centrally." Pages
compute defaults; admins can override per-URL via PageMetadata. Redirects let
ops manage 301s without code deploys. RobotsRule drives /robots.txt.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class PageMetadata(models.Model):
    """
    Per-URL metadata override. If a row exists for `path`, its non-empty fields
    win over whatever the page template computes by default.
    """

    path = models.CharField(
        max_length=400,
        unique=True,
        db_index=True,
        help_text=_('Absolute URL path, e.g. "/products/urea/". Trailing slash required.'),
    )

    title = models.CharField(
        max_length=70, blank=True, help_text=_("Recommended 50–60 chars including brand.")
    )
    description = models.CharField(
        max_length=170, blank=True, help_text=_("Recommended 140–160 chars.")
    )
    canonical_url = models.URLField(
        blank=True, help_text=_("Override the canonical URL. Leave blank to use request URL.")
    )

    og_title = models.CharField(max_length=120, blank=True)
    og_description = models.CharField(max_length=200, blank=True)
    og_image = models.ImageField(
        upload_to="seo/og/", null=True, blank=True, help_text=_("Recommended 1200×630.")
    )

    noindex = models.BooleanField(
        default=False, help_text=_("Adds <meta name=robots content=noindex>.")
    )
    nofollow = models.BooleanField(default=False)

    extra_json_ld = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Optional JSON-LD object merged into the page (overrides per-page default)."),
    )

    notes = models.TextField(blank=True, help_text=_("Internal notes — not rendered."))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Page metadata"
        verbose_name_plural = "Page metadata"
        ordering = ["path"]

    def __str__(self) -> str:
        return self.path


class Redirect(models.Model):
    """
    Admin-managed 301/302 redirects. Applied by SeoRedirectMiddleware.
    Source path is matched verbatim including trailing slash.
    """

    HTTP_PERMANENT = 301
    HTTP_TEMPORARY = 302

    source_path = models.CharField(
        max_length=400,
        unique=True,
        db_index=True,
        help_text=_('e.g. "/old-product/" — match is exact.'),
    )
    target_url = models.CharField(
        max_length=600,
        help_text=_("Either a relative path or an absolute URL."),
    )
    status_code = models.PositiveSmallIntegerField(
        choices=[(301, "301 Permanent"), (302, "302 Temporary")],
        default=HTTP_PERMANENT,
    )

    is_active = models.BooleanField(default=True, db_index=True)
    hits = models.PositiveIntegerField(
        default=0, help_text=_("Increments each time this redirect fires.")
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_path"]
        indexes = [models.Index(fields=["is_active", "source_path"])]

    def __str__(self) -> str:
        return f"{self.source_path} → {self.target_url} ({self.status_code})"


class RobotsRule(models.Model):
    """
    Builds /robots.txt. One row per directive line; rendered in position order.
    Sitemap line is auto-appended by the view.
    """

    DIRECTIVE_CHOICES = [
        ("user_agent", "User-agent"),
        ("disallow", "Disallow"),
        ("allow", "Allow"),
        ("crawl_delay", "Crawl-delay"),
        ("comment", "Comment (# prefix)"),
    ]

    directive = models.CharField(max_length=20, choices=DIRECTIVE_CHOICES)
    value = models.CharField(max_length=400)
    position = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.get_directive_display()}: {self.value}"

    def render_line(self) -> str:
        if self.directive == "comment":
            return f"# {self.value}"
        if self.directive == "user_agent":
            return f"User-agent: {self.value}"
        if self.directive == "disallow":
            return f"Disallow: {self.value}"
        if self.directive == "allow":
            return f"Allow: {self.value}"
        if self.directive == "crawl_delay":
            return f"Crawl-delay: {self.value}"
        return ""
