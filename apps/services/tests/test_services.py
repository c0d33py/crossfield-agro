from __future__ import annotations

from django.urls import reverse

import pytest

from apps.services.models import ServiceCategory, ServiceEnquiry, ServiceOffering
from apps.services.selectors import (
    get_active_offerings,
    get_offering_by_slug,
    get_offerings_by_category,
)
from apps.services.services import submit_service_enquiry
from apps.services.services.enquiry_service import ServiceEnquiryInput

pytestmark = pytest.mark.django_db


def _offer(**kw) -> ServiceOffering:
    kw.setdefault("name", "Agronomy Visit")
    kw.setdefault("slug", "agronomy-visit")
    kw.setdefault("category", ServiceCategory.AGRONOMY)
    kw.setdefault("summary", "On-site agronomy support.")
    return ServiceOffering.objects.create(**kw)


class TestSelectors:
    def test_active_only(self):
        _offer(name="A", slug="a")
        _offer(name="B", slug="b", is_active=False)
        assert list(get_active_offerings().values_list("slug", flat=True)) == ["a"]

    def test_by_slug_returns_only_active(self):
        _offer(slug="hidden", is_active=False)
        assert get_offering_by_slug("hidden") is None

    def test_groups_by_category(self):
        _offer(slug="ag-1", category=ServiceCategory.AGRONOMY, name="Ag 1")
        _offer(slug="cm-1", category=ServiceCategory.MANUFACTURING, name="CM 1")
        grouped = get_offerings_by_category()
        assert "Agronomy support" in grouped
        assert "Contract manufacturing" in grouped


class TestSubmitEnquiry:
    def test_persists_enquiry(self):
        offering = _offer()
        enquiry = submit_service_enquiry(
            enquiry=ServiceEnquiryInput(
                name="A. Buyer",
                email="b@example.com",
                phone="",
                company="Co",
                message="Please visit.",
                offering=offering,
            )
        )
        assert ServiceEnquiry.objects.filter(pk=enquiry.pk).exists()
        assert enquiry.offering_id == offering.pk

    def test_offering_optional(self):
        enquiry = submit_service_enquiry(
            enquiry=ServiceEnquiryInput(
                name="A",
                email="a@x.com",
                phone="",
                company="",
                message="hi",
            )
        )
        assert enquiry.offering is None


class TestListView:
    def test_renders(self, client):
        _offer(name="Field Visit", slug="fv")
        response = client.get(reverse("services:list"))
        assert response.status_code == 200
        assert b"Field Visit" in response.content
        assert b"CollectionPage" in response.content


class TestDetailView:
    def test_404_for_unknown(self, client):
        response = client.get(reverse("services:detail", kwargs={"slug": "nope"}))
        assert response.status_code == 404

    def test_404_for_inactive(self, client):
        _offer(slug="hidden", is_active=False)
        response = client.get(reverse("services:detail", kwargs={"slug": "hidden"}))
        assert response.status_code == 404

    def test_get_renders_form_and_jsonld(self, client):
        _offer(name="Field Visit", slug="fv")
        response = client.get(reverse("services:detail", kwargs={"slug": "fv"}))
        assert response.status_code == 200
        assert b"Field Visit" in response.content
        assert b"<form" in response.content
        assert b'"@type": "Service"' in response.content

    def test_post_valid_creates_enquiry_and_redirects(self, client):
        _offer(slug="fv")
        response = client.post(
            reverse("services:detail", kwargs={"slug": "fv"}),
            data={
                "name": "Test",
                "email": "t@x.com",
                "phone": "",
                "company": "Acme",
                "message": "Visit our farm.",
                "website": "",
            },
        )
        assert response.status_code == 302
        assert ServiceEnquiry.objects.count() == 1

    def test_post_honeypot_rejects(self, client):
        _offer(slug="fv")
        response = client.post(
            reverse("services:detail", kwargs={"slug": "fv"}),
            data={
                "name": "Bot",
                "email": "b@x.com",
                "message": "spam",
                "website": "http://spam",
            },
        )
        # 200 re-render and NO enquiry persisted
        assert response.status_code == 200
        assert ServiceEnquiry.objects.count() == 0

    def test_post_invalid_phone_rejects(self, client):
        _offer(slug="fv")
        response = client.post(
            reverse("services:detail", kwargs={"slug": "fv"}),
            data={
                "name": "Test",
                "email": "t@x.com",
                "phone": "12345",
                "message": "hi",
                "website": "",
            },
        )
        assert response.status_code == 200
        assert b"valid Pakistani mobile" in response.content
        assert ServiceEnquiry.objects.count() == 0
