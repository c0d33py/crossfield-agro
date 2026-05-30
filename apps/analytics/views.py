"""
Lightweight ingestion endpoints called by the front-end beacon.
Same-origin, accepts JSON or form-encoded, no auth required.
"""

from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.analytics.services import record_event, record_pageview


def _client_ip(request: HttpRequest) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_body(request: HttpRequest) -> dict:
    if request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
    return {k: v for k, v in request.POST.items()}


@csrf_exempt
@require_POST
def pageview(request: HttpRequest) -> JsonResponse:
    """
    CSRF-exempt because beacons can't always send the token. Same-origin
    enforced by the browser via fetch (no Origin = block at CORS layer if added).
    """
    data = _parse_body(request)
    path = (data.get("path") or request.path or "/")[:400]
    record_pageview(
        path=path,
        referrer=data.get("referrer", request.META.get("HTTP_REFERER", "")),
        session_key=request.session.session_key or "",
        user=request.user,
        ip=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def event(request: HttpRequest) -> JsonResponse:
    data = _parse_body(request)
    name = data.get("name")
    if not name:
        return JsonResponse({"ok": False, "error": "name required"}, status=400)

    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    record_event(
        name=str(name),
        path=str(data.get("path") or ""),
        session_key=request.session.session_key or "",
        user=request.user,
        metadata=metadata,
    )
    return JsonResponse({"ok": True})
