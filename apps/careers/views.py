from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from apps.careers.forms import JobApplicationForm
from apps.careers.selectors import get_posting_by_slug, get_postings_by_department
from apps.careers.services import ApplicationInput, submit_application


def _client_ip(request: HttpRequest) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class CareersListView(View):
    template_name = "careers/job_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"grouped": get_postings_by_department()})


class CareersDetailView(View):
    template_name = "careers/job_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        posting = get_posting_by_slug(slug)
        if posting is None:
            raise Http404("Posting not found")
        form = JobApplicationForm() if posting.is_open else None
        return render(request, self.template_name, {"posting": posting, "form": form})

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        posting = get_posting_by_slug(slug)
        if posting is None:
            raise Http404("Posting not found")
        if not posting.is_open:
            messages.error(request, "This posting is no longer accepting applications.")
            return HttpResponseRedirect(posting.get_absolute_url())

        form = JobApplicationForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"posting": posting, "form": form})

        try:
            submit_application(
                payload=ApplicationInput(
                    posting=posting,
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                    location=form.cleaned_data["location"],
                    cv=form.cleaned_data["cv"],
                    cover_letter=form.cleaned_data["cover_letter"],
                    linkedin_url=form.cleaned_data["linkedin_url"],
                    submitter_ip=_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
            )
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return render(request, self.template_name, {"posting": posting, "form": form})

        messages.success(
            request,
            f"Thank you — your application for {posting.title} has been received. "
            "We respond to every qualified application within 5–10 business days.",
        )
        return HttpResponseRedirect(reverse("careers:detail", kwargs={"slug": slug}))
