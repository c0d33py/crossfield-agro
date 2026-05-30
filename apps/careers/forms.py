from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

PK_PHONE = re.compile(r"^(\+92|0092|0)[\s-]?3\d{2}[\s-]?\d{7}$")
CV_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
CV_ALLOWED_EXT = {"pdf", "doc", "docx"}


class JobApplicationForm(forms.Form):
    full_name = forms.CharField(max_length=140, label="Full name")
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    location = forms.CharField(
        max_length=140, required=False, help_text="Where you're based today (city, country)."
    )

    cv = forms.FileField(
        label="CV / Résumé",
        help_text="PDF, DOC, or DOCX up to 5 MB.",
    )
    cover_letter = forms.CharField(
        widget=forms.Textarea,
        max_length=4000,
        required=False,
        label="Cover letter (optional)",
        help_text="Why this role, why Crosfield.",
    )
    linkedin_url = forms.URLField(required=False, label="LinkedIn profile (optional)")

    # Honeypot
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_phone(self) -> str:
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not PK_PHONE.match(phone):
            raise ValidationError("Enter a valid Pakistani mobile number (e.g. +92 3xx xxxxxxx).")
        return phone

    def clean_cv(self):
        cv = self.cleaned_data.get("cv")
        if not cv:
            raise ValidationError("CV is required.")
        if cv.size > CV_MAX_BYTES:
            raise ValidationError("CV must be 5 MB or smaller.")
        ext = (cv.name.rsplit(".", 1)[-1] or "").lower()
        if ext not in CV_ALLOWED_EXT:
            raise ValidationError("CV must be a PDF, DOC, or DOCX file.")
        return cv

    def clean_website(self) -> str:
        if self.cleaned_data.get("website"):
            raise ValidationError("Bot detected.")
        return ""
