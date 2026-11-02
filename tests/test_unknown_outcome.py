from decimal import Decimal
from http import HTTPStatus

import pytest
from flask import Flask

from coffer.models import Cart, User, UserPaymentMethod
from coffer.provider import PaymentProvider
from tests.shop import Shop, assert_error


class TimingOutProvider:
    """Never answers, so nobody knows whether the card was charged."""

    def charge(
        self, token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> str:
        raise TimeoutError


@pytest.fixture
def provider() -> PaymentProvider:
    return TimingOutProvider()


def test_an_unknown_outcome_keeps_the_payment_pending_and_blocks_a_retry(
    app: Flask, shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod
) -> None:
    app.testing = False

    first = shop.pay(cart.id, alice)
    retry = shop.pay(cart.id, alice)

    assert first.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert_error(retry, HTTPStatus.CONFLICT, "payment_in_progress")
    assert [payment.status for payment in shop.payments(cart)] == ["pending"]
    assert shop.cart_status(cart) == "active"
