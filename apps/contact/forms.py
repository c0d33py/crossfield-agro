from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.contact.models import EnquiryType

PK_PHONE = re.compile(r"^(\+92|0092|0)[\s-]?3\d{2}[\s-]?\d{7}$")


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    company = forms.CharField(max_length=140, required=False)
    enquiry_type = forms.ChoiceField(choices=EnquiryType.choices)
    message = forms.CharField(widget=forms.Textarea, max_length=4000)
    # Honeypot
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_phone(self) -> str:
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not PK_PHONE.match(phone):
            raise ValidationError("Enter a valid Pakistani mobile number (e.g. +92 3xx xxxxxxx).")
        return phone

    def clean_website(self) -> str:
        if self.cleaned_data.get("website"):
            raise ValidationError("Bot detected.")
        return ""
