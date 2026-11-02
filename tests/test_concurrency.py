import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from http import HTTPStatus

import pytest

from coffer.models import Cart, User, UserPaymentMethod
from tests.shop import Shop, assert_error
from tests.spy_provider import SpyProvider

TIMEOUT_SECONDS = 5


class BlockingProvider(SpyProvider):
    """Holds every charge inside the provider call until the test releases it."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def charge(
        self, token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> str:
        self.entered.set()
        if not self.release.wait(TIMEOUT_SECONDS):
            raise TimeoutError
        return super().charge(token, amount, currency, idempotency_key)


@pytest.fixture
def provider() -> BlockingProvider:
    return BlockingProvider()


def test_a_second_request_during_the_charge_never_charges_twice(
    shop: Shop,
    alice: User,
    cart: Cart,
    card: UserPaymentMethod,
    provider: BlockingProvider,
) -> None:
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(shop.pay, cart.id, alice)
        assert provider.entered.wait(TIMEOUT_SECONDS)

        second = shop.pay(cart.id, alice)
        provider.release.set()
        first_response = first.result(TIMEOUT_SECONDS)

    assert_error(second, HTTPStatus.CONFLICT, "payment_in_progress")
    assert first_response.status_code == HTTPStatus.CREATED
    assert len(provider.charges) == 1
    assert [payment.status for payment in shop.payments(cart)] == ["succeeded"]
