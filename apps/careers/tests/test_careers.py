from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.careers.models import (
    Department,
    EmploymentType,
    ExperienceLevel,
    JobApplication,
    JobPosting,
    PostingStatus,
)
from apps.careers.selectors import get_open_postings, get_posting_by_slug

pytestmark = pytest.mark.django_db


def _dept(name="R&D", slug="r-d") -> Department:
    return Department.objects.create(name=name, slug=slug, is_active=True)


def _posting(dept=None, status=PostingStatus.OPEN, **kw) -> JobPosting:
    if dept is None:
        dept = _dept()
    kw.setdefault("title", "Formulation Chemist")
    kw.setdefault("slug", "formulation-chemist")
    kw.setdefault("location", "Lahore")
    kw.setdefault("employment_type", EmploymentType.FULL_TIME)
    kw.setdefault("experience_level", ExperienceLevel.MID)
    kw.setdefault("summary", "Develop and scale new formulations.")
    kw.setdefault("description", "Long description.")
    if status == PostingStatus.OPEN:
        kw.setdefault("published_at", timezone.now())
    return JobPosting.objects.create(department=dept, status=status, **kw)


class TestSelectors:
    def test_open_postings_only(self):
        dept = _dept()
        _posting(dept=dept, slug="open", title="Open Role")
        _posting(dept=dept, slug="closed", title="Closed Role", status=PostingStatus.CLOSED)
        slugs = list(get_open_postings().values_list("slug", flat=True))
        assert slugs == ["open"]

    def test_closes_at_in_past_excluded(self):
        _posting(slug="expired", closes_at=timezone.now() - timezone.timedelta(days=1))
        assert get_open_postings().count() == 0

    def test_by_slug_returns_any_status(self):
        _posting(slug="closed", status=PostingStatus.CLOSED)
        assert get_posting_by_slug("closed") is not None


class TestListView:
    def test_renders_grouped(self, client):
        _posting(slug="rd-1", title="R&D 1")
        response = client.get(reverse("careers:list"))
        assert response.status_code == 200
        assert b"R&amp;D" in response.content
        assert b"R&amp;D 1" in response.content

    def test_empty_state(self, client):
        response = client.get(reverse("careers:list"))
        assert response.status_code == 200
        assert b"No open roles right now" in response.content


class TestDetailView:
    def test_404_for_unknown(self, client):
        response = client.get(reverse("careers:detail", kwargs={"slug": "nope"}))
        assert response.status_code == 404

    def test_renders_form_when_open(self, client):
        _posting(slug="open-role", title="Open Role")
        response = client.get(reverse("careers:detail", kwargs={"slug": "open-role"}))
        assert response.status_code == 200
        assert b"Open Role" in response.content
        assert b'"@type": "JobPosting"' in response.content
        assert b"Submit Application" in response.content

    def test_closed_role_no_form(self, client):
        _posting(slug="closed", title="Closed", status=PostingStatus.CLOSED)
        response = client.get(reverse("careers:detail", kwargs={"slug": "closed"}))
        assert response.status_code == 200
        assert b"no longer accepting applications" in response.content


class TestApplyFlow:
    def _cv(self) -> SimpleUploadedFile:
        return SimpleUploadedFile("cv.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

    def test_valid_application_persisted(self, client):
        _posting(slug="role-1")
        response = client.post(
            reverse("careers:detail", kwargs={"slug": "role-1"}),
            data={
                "full_name": "A Candidate",
                "email": "c@x.com",
                "phone": "",
                "location": "Lahore",
                "cv": self._cv(),
                "cover_letter": "Why I'd be a fit.",
                "linkedin_url": "",
                "website": "",
            },
        )
        assert response.status_code == 302
        assert JobApplication.objects.count() == 1

    def test_rejects_non_pdf(self, client):
        _posting(slug="role-2")
        bad = SimpleUploadedFile("cv.txt", b"text", content_type="text/plain")
        response = client.post(
            reverse("careers:detail", kwargs={"slug": "role-2"}),
            data={
                "full_name": "X",
                "email": "x@x.com",
                "cv": bad,
                "website": "",
            },
        )
        assert response.status_code == 200
        assert b"PDF, DOC, or DOCX" in response.content
        assert JobApplication.objects.count() == 0

    def test_honeypot_rejects(self, client):
        _posting(slug="role-3")
        response = client.post(
            reverse("careers:detail", kwargs={"slug": "role-3"}),
            data={
                "full_name": "Bot",
                "email": "b@x.com",
                "cv": self._cv(),
                "website": "http://spam",
            },
        )
        assert response.status_code == 200
        assert JobApplication.objects.count() == 0
