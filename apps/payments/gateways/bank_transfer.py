"""
Manual / bank-transfer / COD "gateway".
- create_intent simply records intent and returns a confirmation URL.
- Staff confirms receipt via admin, which triggers a synthetic webhook event.
Common for Pakistani B2B agro buyers.
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


class BankTransferAdapter(GatewayAdapter):
    name = "bank_transfer"

    def create_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        return_url: str,
        webhook_url: str,
    ) -> IntentResponse:
        intent_id = f"bt_{secrets.token_hex(8)}"
        return IntentResponse(
            gateway=self.name,
            intent_id=intent_id,
            redirect_url=return_url,
        )

    def verify_signature(self, payload: bytes, signature: str) -> None:
        # Synthetic events are produced internally; no signature needed.
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
        # Manual gateway has no remote status — admin drives state changes
        return GatewayStatus(intent_id=intent_id, is_terminal=False, succeeded=False)


register_gateway("bank_transfer", BankTransferAdapter())
