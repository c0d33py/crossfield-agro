from __future__ import annotations

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from apps.services.forms import ServiceEnquiryForm
from apps.services.selectors import get_offering_by_slug, get_offerings_by_category
from apps.services.services import submit_service_enquiry
from apps.services.services.enquiry_service import ServiceEnquiryInput


class ServiceListView(View):
    template_name = "services/service_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"grouped": get_offerings_by_category()},
        )


class ServiceDetailView(View):
    template_name = "services/service_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        offering = get_offering_by_slug(slug)
        if offering is None:
            raise Http404("Service not found")
        return render(
            request,
            self.template_name,
            {"offering": offering, "form": ServiceEnquiryForm()},
        )

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        offering = get_offering_by_slug(slug)
        if offering is None:
            raise Http404("Service not found")

        form = ServiceEnquiryForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"offering": offering, "form": form},
            )

        submit_service_enquiry(
            enquiry=ServiceEnquiryInput(
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                phone=form.cleaned_data["phone"],
                company=form.cleaned_data["company"],
                message=form.cleaned_data["message"],
                offering=offering,
            )
        )
        messages.success(
            request,
            f"Thanks — your enquiry about “{offering.name}” has been received. "
            "We'll respond within one business day.",
        )
        return HttpResponseRedirect(reverse("services:detail", kwargs={"slug": slug}))
