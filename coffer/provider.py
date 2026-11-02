"""The payment provider behind a small interface, and the mock standing in for it."""

from decimal import Decimal
from typing import Protocol
from uuid import uuid4


class CardDeclinedError(Exception):
    """The provider refused to charge the card."""


class ProviderUnavailableError(Exception):
    """The provider confirmed it charged nothing, so the cart can be paid again."""


class PaymentProvider(Protocol):
    def charge(
        self, token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> str:
        """Charge the card and return the charge id. The key stops a duplicate."""
        ...


class MockPaymentProvider:
    """Declines a token containing "decline", is down for "unavailable"."""

    def charge(
        self, token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> str:
        if "decline" in token:
            raise CardDeclinedError
        if "unavailable" in token:
            raise ProviderUnavailableError
        return f"mock_ch_{uuid4().hex}"
