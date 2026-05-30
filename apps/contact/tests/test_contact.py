from __future__ import annotations

from django.urls import reverse

import pytest

from apps.contact.models import ContactMessage, ContactStatus, EnquiryType
from apps.contact.services import ContactMessageInput, submit_contact_message

pytestmark = pytest.mark.django_db


VALID = {
    "name": "A Buyer",
    "email": "buyer@example.com",
    "phone": "",
    "company": "Acme Pakistan",
    "enquiry_type": "sales",
    "message": "Please send a quote for 5 tonnes urea.",
    "website": "",
}


class TestSubmitService:
    def test_persists_message(self):
        msg = submit_contact_message(
            payload=ContactMessageInput(
                name="X",
                email="x@x.com",
                phone="",
                company="",
                enquiry_type=EnquiryType.SALES,
                message="hi",
            )
        )
        assert ContactMessage.objects.filter(pk=msg.pk).exists()
        assert msg.status == ContactStatus.NEW


class TestContactView:
    def test_get_renders_form(self, client):
        response = client.get(reverse("contact:form"))
        assert response.status_code == 200
        assert b"Contact us" in response.content
        assert b"<form" in response.content
        assert b"Pakistani" in response.content  # phone help text

    def test_valid_post_creates_and_redirects(self, client):
        response = client.post(reverse("contact:form"), data=VALID)
        assert response.status_code == 302
        assert ContactMessage.objects.count() == 1
        msg = ContactMessage.objects.first()
        assert msg.email == "buyer@example.com"
        assert msg.enquiry_type == "sales"

    def test_invalid_phone_rejected(self, client):
        bad = dict(VALID, phone="not-a-number")
        response = client.post(reverse("contact:form"), data=bad)
        assert response.status_code == 200
        assert b"valid Pakistani mobile" in response.content
        assert ContactMessage.objects.count() == 0

    def test_honeypot_rejects_silently(self, client):
        bot = dict(VALID, website="http://spam.example")
        response = client.post(reverse("contact:form"), data=bot)
        assert response.status_code == 200
        assert ContactMessage.objects.count() == 0

    def test_records_submitter_ip(self, client):
        client.post(reverse("contact:form"), data=VALID, REMOTE_ADDR="203.0.113.42")
        msg = ContactMessage.objects.first()
        assert msg.submitter_ip == "203.0.113.42"
