from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from apps.contact.forms import ContactForm
from apps.contact.services import ContactMessageInput, submit_contact_message


def _client_ip(request: HttpRequest) -> str | None:
    """Best-effort client IP — respects X-Forwarded-For when behind a proxy."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class ContactView(View):
    template_name = "contact/contact.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": ContactForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ContactForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        submit_contact_message(
            payload=ContactMessageInput(
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                phone=form.cleaned_data["phone"],
                company=form.cleaned_data["company"],
                enquiry_type=form.cleaned_data["enquiry_type"],
                message=form.cleaned_data["message"],
                submitter_ip=_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        )
        messages.success(
            request,
            "Thanks — your enquiry has been received. We'll respond within one business day.",
        )
        return HttpResponseRedirect(reverse("contact:form"))
