from django import forms


class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "type": "search",
                "placeholder": "Search products…",
                "autocomplete": "off",
                "aria-label": "Search products",
            }
        ),
    )
