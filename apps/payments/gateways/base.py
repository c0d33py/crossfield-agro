"""
Gateway adapter interface. Each concrete gateway implements GatewayAdapter.
Use get_gateway(name) to retrieve a configured instance.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal


class WebhookSignatureError(Exception):
    """Raised when the gateway signature does not verify."""


class WebhookParseError(Exception):
    """Raised when the webhook payload cannot be parsed."""


@dataclass(frozen=True)
class IntentResponse:
    gateway: str
    intent_id: str
    redirect_url: str
    client_token: str | None = None


@dataclass(frozen=True)
class GatewayEvent:
    event_id: str
    type: str  # "payment.succeeded" | "payment.failed" | ...
    intent_id: str
    failure_reason: str = ""


@dataclass(frozen=True)
class GatewayStatus:
    intent_id: str
    is_terminal: bool
    succeeded: bool


class GatewayAdapter(abc.ABC):
    name: str

    @abc.abstractmethod
    def create_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        return_url: str,
        webhook_url: str,
    ) -> IntentResponse: ...

    @abc.abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> None: ...

    @abc.abstractmethod
    def parse(self, payload: bytes) -> GatewayEvent: ...

    @abc.abstractmethod
    def fetch_status(self, intent_id: str) -> GatewayStatus: ...


_REGISTRY: dict[str, GatewayAdapter] = {}


def register_gateway(name: str, adapter: GatewayAdapter) -> None:
    _REGISTRY[name] = adapter


def get_gateway(name: str) -> GatewayAdapter:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown payment gateway: {name}") from exc
