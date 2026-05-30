from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

GATEWAY_CHOICES = [
    ("cod", "Cash on Delivery"),
    ("bank_transfer", "Bank Transfer"),
    # ("jazzcash",      "JazzCash"),
    # ("easypaisa",     "EasyPaisa"),
]

PK_PHONE = re.compile(r"^(\+92|0092|0)[\s-]?3\d{2}[\s-]?\d{7}$")


def _validate_pk_phone(value: str) -> str:
    if value and not PK_PHONE.match(value):
        raise ValidationError("Enter a valid Pakistani mobile number (e.g. +92 3xx xxxxxxx).")
    return value


# ---------------------------------------------------------------------------
# 3-step checkout forms
# Each step posts to its own URL; data persists in request.session['checkout'].
# ---------------------------------------------------------------------------


class AddressForm(forms.Form):
    """Step 1: contact + shipping + billing addresses."""

    email = forms.EmailField()

    shipping_name = forms.CharField(max_length=120, label="Full name")
    shipping_line1 = forms.CharField(max_length=200, label="Address line 1")
    shipping_line2 = forms.CharField(
        max_length=200, required=False, label="Address line 2 (optional)"
    )
    shipping_city = forms.CharField(max_length=80, label="City")
    shipping_postal_code = forms.CharField(max_length=10, label="Postal code")
    shipping_country = forms.CharField(max_length=2, initial="PK", label="Country (ISO code)")
    shipping_phone = forms.CharField(max_length=20, label="Phone")

    billing_same_as_shipping = forms.BooleanField(
        required=False, initial=True, label="Billing address same as shipping"
    )

    billing_name = forms.CharField(max_length=120, required=False, label="Full name (billing)")
    billing_line1 = forms.CharField(
        max_length=200, required=False, label="Address line 1 (billing)"
    )
    billing_line2 = forms.CharField(
        max_length=200, required=False, label="Address line 2 (billing)"
    )
    billing_city = forms.CharField(max_length=80, required=False, label="City (billing)")
    billing_postal_code = forms.CharField(
        max_length=10, required=False, label="Postal code (billing)"
    )
    billing_country = forms.CharField(max_length=2, required=False, label="Country (billing)")

    def clean_shipping_phone(self) -> str:
        return _validate_pk_phone(self.cleaned_data.get("shipping_phone", ""))

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("billing_same_as_shipping", True):
            for field in (
                "billing_name",
                "billing_line1",
                "billing_city",
                "billing_postal_code",
                "billing_country",
            ):
                if not cleaned.get(field):
                    self.add_error(field, "Required when billing differs from shipping.")
        return cleaned

    def to_session(self) -> dict:
        d = self.cleaned_data
        return {
            "email": d["email"],
            "shipping": {
                "name": d["shipping_name"],
                "line1": d["shipping_line1"],
                "line2": d.get("shipping_line2", ""),
                "city": d["shipping_city"],
                "postal_code": d["shipping_postal_code"],
                "country": d["shipping_country"],
                "phone": d["shipping_phone"],
            },
            "billing_same": bool(d.get("billing_same_as_shipping", True)),
            "billing": (
                {
                    "name": d["shipping_name"],
                    "line1": d["shipping_line1"],
                    "line2": d.get("shipping_line2", ""),
                    "city": d["shipping_city"],
                    "postal_code": d["shipping_postal_code"],
                    "country": d["shipping_country"],
                }
                if d.get("billing_same_as_shipping", True)
                else {
                    "name": d["billing_name"],
                    "line1": d["billing_line1"],
                    "line2": d.get("billing_line2", ""),
                    "city": d["billing_city"],
                    "postal_code": d["billing_postal_code"],
                    "country": d["billing_country"],
                }
            ),
        }


class PaymentForm(forms.Form):
    """Step 3: choose payment gateway."""

    gateway = forms.ChoiceField(choices=GATEWAY_CHOICES, widget=forms.RadioSelect)
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the terms & conditions and authorise this order.",
    )


# ---------------------------------------------------------------------------
# Legacy single-page form — kept for back-compat with existing tests.
# ---------------------------------------------------------------------------


class CheckoutForm(forms.Form):
    email = forms.EmailField()

    shipping_name = forms.CharField(max_length=120)
    shipping_line1 = forms.CharField(max_length=200)
    shipping_line2 = forms.CharField(max_length=200, required=False)
    shipping_city = forms.CharField(max_length=80)
    shipping_postal_code = forms.CharField(max_length=10)
    shipping_country = forms.CharField(max_length=2, initial="PK")
    shipping_phone = forms.CharField(max_length=20)

    billing_same_as_shipping = forms.BooleanField(required=False, initial=True)

    billing_name = forms.CharField(max_length=120, required=False)
    billing_line1 = forms.CharField(max_length=200, required=False)
    billing_line2 = forms.CharField(max_length=200, required=False)
    billing_city = forms.CharField(max_length=80, required=False)
    billing_postal_code = forms.CharField(max_length=10, required=False)
    billing_country = forms.CharField(max_length=2, required=False)

    gateway = forms.ChoiceField(choices=GATEWAY_CHOICES)

    def addresses(self) -> tuple[dict, dict]:
        d = self.cleaned_data
        shipping = {
            "name": d["shipping_name"],
            "line1": d["shipping_line1"],
            "line2": d.get("shipping_line2", ""),
            "city": d["shipping_city"],
            "postal_code": d["shipping_postal_code"],
            "country": d["shipping_country"],
            "phone": d["shipping_phone"],
        }
        if d.get("billing_same_as_shipping", True):
            billing = dict(shipping)
        else:
            billing = {
                "name": d["billing_name"],
                "line1": d["billing_line1"],
                "line2": d.get("billing_line2", ""),
                "city": d["billing_city"],
                "postal_code": d["billing_postal_code"],
                "country": d["billing_country"],
            }
        return shipping, billing
