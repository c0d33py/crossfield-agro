from __future__ import annotations

from django import forms


class OrderTrackForm(forms.Form):
    """Public tracking: order number only. Rate-limited at the view layer."""

    order_number = forms.CharField(
        max_length=32,
        label="Order number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "CA-20260528-XXXXXX",
                "autocomplete": "off",
                "spellcheck": "false",
            }
        ),
    )

    def clean_order_number(self) -> str:
        # Strip and normalise — users paste with spaces or lowercase.
        return self.cleaned_data["order_number"].strip().upper()
