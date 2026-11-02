from decimal import Decimal

import pytest

from coffer.provider import (
    CardDeclinedError,
    MockPaymentProvider,
    ProviderUnavailableError,
)


def charge(token: str) -> str:
    return MockPaymentProvider().charge(
        token, Decimal("70.00"), "USD", idempotency_key="payment-1"
    )


def test_charges_a_card_and_returns_a_unique_reference() -> None:
    first, second = charge("tok_test_visa"), charge("tok_test_visa")

    assert first.startswith("mock_ch_")
    assert first != second


def test_declines_a_token_containing_decline() -> None:
    with pytest.raises(CardDeclinedError):
        charge("tok_test_bob_decline")


def test_is_unavailable_for_a_token_containing_unavailable() -> None:
    with pytest.raises(ProviderUnavailableError):
        charge("tok_test_dave_unavailable")
