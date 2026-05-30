from __future__ import annotations

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.cart.services import merge_session_cart_into_user_cart


@receiver(user_logged_in)
def _merge_carts_on_login(sender, request, user, **kwargs) -> None:
    session_key = request.session.session_key
    if not session_key:
        return
    merge_session_cart_into_user_cart(session_key=session_key, user=user)
