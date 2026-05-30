"""
Cash on Delivery gateway.

Semantics differ from bank_transfer: COD orders proceed through fulfillment
(CONFIRMED -> PROCESSING -> SHIPPED -> DELIVERED) WITHOUT being paid. Cash is
collected by the courier on delivery. Staff confirms receipt afterwards via
the PaymentAdmin "Mark COD payment received" action, which fires a synthetic
succeeded event through the normal webhook pipeline (so stock decrement,
invoice generation, and audit trail all run uniformly).
"""

from __future__ import annotations

import secrets
from decimal import Decimal

from .base import (
    GatewayAdapter,
    GatewayEvent,
    GatewayStatus,
    IntentResponse,
    WebhookParseError,
    register_gateway,
)


class CashOnDeliveryAdapter(GatewayAdapter):
    name = "cod"

    def create_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        return_url: str,
        webhook_url: str,
    ) -> IntentResponse:
        intent_id = f"cod_{secrets.token_hex(8)}"
        return IntentResponse(
            gateway=self.name,
            intent_id=intent_id,
            redirect_url=return_url,
        )

    def verify_signature(self, payload: bytes, signature: str) -> None:
        # Synthetic events produced internally by staff actions; no signature.
        return

    def parse(self, payload: bytes) -> GatewayEvent:
        import json

        try:
            data = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise WebhookParseError(str(e)) from e
        return GatewayEvent(
            event_id=data["event_id"],
            type=data["type"],
            intent_id=data["intent_id"],
            failure_reason=data.get("failure_reason", ""),
        )

    def fetch_status(self, intent_id: str) -> GatewayStatus:
        # No remote system; reconciliation never advances a COD payment.
        return GatewayStatus(intent_id=intent_id, is_terminal=False, succeeded=False)


register_gateway("cod", CashOnDeliveryAdapter())
