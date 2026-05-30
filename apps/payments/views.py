from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments.gateways import WebhookParseError, WebhookSignatureError
from apps.payments.services import handle_webhook

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def payment_webhook(request: HttpRequest, gateway_name: str) -> HttpResponse:
    """
    Gateway POSTs here. Verify signature BEFORE processing. Idempotent on
    (gateway, event_id). Always return 200 on a duplicate.
    """
    signature = request.headers.get("X-Gateway-Signature", "")
    try:
        handle_webhook(gateway_name=gateway_name, payload=request.body, signature=signature)
    except WebhookSignatureError:
        logger.warning("Bad signature for %s webhook", gateway_name)
        return HttpResponse(status=401)
    except WebhookParseError:
        return HttpResponse(status=400)
    except Exception:
        logger.exception("Unhandled webhook error for %s", gateway_name)
        return HttpResponse(status=500)
    return HttpResponse(status=200)
