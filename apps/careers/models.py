"""
Careers — Department + JobPosting + JobApplication.

JobApplication is immutable record of an application; staff manage status via admin.
File uploads (CV) go to MEDIA_ROOT/careers/cvs/YYYY/MM/.
"""

from __future__ import annotations

from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", _("Full-time")
    PART_TIME = "part_time", _("Part-time")
    CONTRACT = "contract", _("Contract")
    INTERNSHIP = "internship", _("Internship")


class ExperienceLevel(models.TextChoices):
    ENTRY = "entry", _("Entry level")
    MID = "mid", _("Mid level")
    SENIOR = "senior", _("Senior")
    LEAD = "lead", _("Lead / Manager")


class PostingStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")


class ApplicationStatus(models.TextChoices):
    NEW = "new", _("New")
    REVIEWING = "reviewing", _("Reviewing")
    SHORTLISTED = "shortlisted", _("Shortlisted")
    INTERVIEWED = "interviewed", _("Interviewed")
    OFFERED = "offered", _("Offered")
    HIRED = "hired", _("Hired")
    REJECTED = "rejected", _("Rejected")
    WITHDRAWN = "withdrawn", _("Withdrawn")


class Department(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class JobPosting(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)

    department = models.ForeignKey(Department, related_name="postings", on_delete=models.PROTECT)
    location = models.CharField(max_length=140, help_text=_('e.g. "Lahore, Punjab"'))
    employment_type = models.CharField(
        max_length=24,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    experience_level = models.CharField(
        max_length=24,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.MID,
    )

    summary = models.CharField(max_length=300)
    description = models.TextField(help_text=_("Role description, day-to-day, what you'll do."))
    responsibilities = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=16,
        choices=PostingStatus.choices,
        default=PostingStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    closes_at = models.DateTimeField(
        null=True, blank=True, help_text=_("Optional application deadline.")
    )

    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=170, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["department", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.department.name})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("careers:detail", kwargs={"slug": self.slug})

    @property
    def is_open(self) -> bool:
        from django.utils import timezone

        if self.status != PostingStatus.OPEN:
            return False
        if self.published_at is None or self.published_at > timezone.now():
            return False
        if self.closes_at and self.closes_at < timezone.now():
            return False
        return True


def _cv_upload_path(instance, filename: str) -> str:
    return (
        f"careers/cvs/{instance.created_at:%Y/%m/}/{filename}"
        if instance.pk
        else f"careers/cvs/uploads/{filename}"
    )


class JobApplication(models.Model):
    posting = models.ForeignKey(JobPosting, related_name="applications", on_delete=models.PROTECT)

    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(
        max_length=140, blank=True, help_text=_("Where the applicant is based today.")
    )

    cv = models.FileField(
        upload_to=_cv_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
        help_text=_("PDF, DOC, or DOCX up to 5 MB."),
    )
    cover_letter = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=24,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.NEW,
        db_index=True,
    )
    internal_notes = models.TextField(blank=True)

    submitter_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["posting", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} → {self.posting.title}"
