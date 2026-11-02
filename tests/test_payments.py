from decimal import Decimal
from http import HTTPStatus
from uuid import uuid4

import pytest
from flask.testing import FlaskClient

from coffer.models import Cart, User, UserPaymentMethod
from tests.shop import Shop, assert_error
from tests.spy_provider import Charge, SpyProvider


def test_charges_the_cart_and_checks_it_out(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod
) -> None:
    response = shop.pay(cart.id, alice)

    assert response.status_code == HTTPStatus.CREATED
    [payment] = shop.payments(cart)
    assert response.json == {
        "id": str(payment.id),
        "cart_id": str(cart.id),
        "status": "succeeded",
        "amount": "70.00",
        "currency": "USD",
        "created_at": payment.created_at.isoformat(),
    }
    assert payment.created_at.tzinfo is not None
    assert payment.status == "succeeded"
    assert payment.amount == Decimal("70.00")
    assert payment.payment_method_id == card.id
    assert payment.provider_reference is not None
    assert payment.provider_reference.startswith("mock_ch_")
    assert shop.cart_status(cart) == "checked_out"


def test_charges_the_server_side_total_once_per_payment_with_no_transaction_open(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod, provider: SpyProvider
) -> None:
    shop.pay(cart.id, alice)

    [payment] = shop.payments(cart)
    assert provider.charges == [
        Charge(
            token="tok_test_visa",
            amount=Decimal("70.00"),
            currency="USD",
            idempotency_key=str(payment.id),
            in_transaction=False,
        )
    ]


def test_uses_the_most_recent_default_card(
    shop: Shop, alice: User, cart: Cart, provider: SpyProvider
) -> None:
    shop.card(alice, "tok_old_default")
    shop.card(alice, "tok_new_default")
    shop.card(alice, "tok_not_default", is_default=False)

    shop.pay(cart.id, alice)

    assert [charge.token for charge in provider.charges] == ["tok_new_default"]


def test_a_declined_card_answers_402_and_keeps_the_cart_open(
    shop: Shop, alice: User, cart: Cart
) -> None:
    shop.card(alice, "tok_test_decline")

    response = shop.pay(cart.id, alice)

    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    [payment] = shop.payments(cart)
    assert response.json == {
        "error": {
            "code": "card_declined",
            "message": "The card was declined.",
            "payment_id": str(payment.id),
        }
    }
    assert (payment.status, payment.failure_reason) == ("failed", "card_declined")
    assert shop.cart_status(cart) == "active"


def test_the_cart_can_be_paid_after_a_decline(
    shop: Shop, alice: User, cart: Cart
) -> None:
    shop.card(alice, "tok_test_decline")
    shop.pay(cart.id, alice)
    shop.card(alice, "tok_test_visa")

    response = shop.pay(cart.id, alice)

    assert response.status_code == HTTPStatus.CREATED
    statuses = sorted(payment.status for payment in shop.payments(cart))
    assert statuses == ["failed", "succeeded"]


def test_an_unavailable_provider_answers_502_and_keeps_the_cart_open(
    shop: Shop, alice: User, cart: Cart
) -> None:
    shop.card(alice, "tok_test_unavailable")

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.BAD_GATEWAY, "provider_unavailable")
    [payment] = shop.payments(cart)
    assert response.json is not None
    assert response.json["error"]["payment_id"] == str(payment.id)
    assert (payment.status, payment.failure_reason) == (
        "failed",
        "provider_unavailable",
    )
    assert shop.cart_status(cart) == "active"


def test_rejects_a_request_without_a_bearer_token(
    client: FlaskClient, cart: Cart, card: UserPaymentMethod, provider: SpyProvider
) -> None:
    response = client.post(f"/carts/{cart.id}/payments")

    assert_error(response, HTTPStatus.UNAUTHORIZED, "unauthorized")
    assert provider.charges == []


def test_answers_another_users_cart_exactly_like_a_missing_one(
    shop: Shop, cart: Cart, provider: SpyProvider
) -> None:
    bob = shop.user("bob")

    other_users_cart = shop.pay(cart.id, bob)
    missing_cart = shop.pay(uuid4(), bob)

    assert other_users_cart.status_code == HTTPStatus.NOT_FOUND
    assert (
        other_users_cart.json
        == missing_cart.json
        == {"error": {"code": "cart_not_found", "message": "Cart not found."}}
    )
    assert provider.charges == []
    assert shop.cart_status(cart) == "active"


def test_a_malformed_cart_id_is_not_found(client: FlaskClient) -> None:
    response = client.post("/carts/not-a-uuid/payments")

    assert_error(response, HTTPStatus.NOT_FOUND, "not_found")


def test_an_abandoned_cart_cannot_be_paid(
    shop: Shop, alice: User, card: UserPaymentMethod, provider: SpyProvider
) -> None:
    cart = shop.cart(alice, status="abandoned")

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.CONFLICT, "cart_not_active")
    assert provider.charges == []


def test_paying_a_paid_cart_again_charges_nothing(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod, provider: SpyProvider
) -> None:
    shop.pay(cart.id, alice)

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.CONFLICT, "cart_not_active")
    assert len(provider.charges) == 1


def test_refuses_a_payment_while_another_is_pending(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod, provider: SpyProvider
) -> None:
    shop.payment(cart, card)

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.CONFLICT, "payment_in_progress")
    assert provider.charges == []
    assert len(shop.payments(cart)) == 1


@pytest.mark.parametrize("items", [(), (("0.00", 1),)], ids=["empty", "free"])
def test_a_cart_without_a_positive_total_has_nothing_to_pay(
    shop: Shop,
    alice: User,
    card: UserPaymentMethod,
    provider: SpyProvider,
    items: tuple[tuple[str, int], ...],
) -> None:
    cart = shop.cart(alice, items=items)

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.UNPROCESSABLE_CONTENT, "nothing_to_pay")
    assert provider.charges == []
    assert shop.payments(cart) == []


@pytest.mark.parametrize("saved_cards", [0, 1], ids=["no card", "no default"])
def test_a_user_without_a_default_card_cannot_pay(
    shop: Shop, alice: User, cart: Cart, provider: SpyProvider, saved_cards: int
) -> None:
    for _ in range(saved_cards):
        shop.card(alice, is_default=False)

    response = shop.pay(cart.id, alice)

    assert_error(response, HTTPStatus.UNPROCESSABLE_CONTENT, "no_payment_method")
    assert provider.charges == []


@pytest.mark.parametrize(
    ("token", "outcome"),
    [
        ("tok_test_visa", "succeeded"),
        ("tok_test_decline", "card_declined"),
        ("tok_test_unavailable", "provider_unavailable"),
    ],
)
def test_logs_each_outcome_once_and_never_exposes_the_card_token(
    shop: Shop,
    alice: User,
    cart: Cart,
    caplog: pytest.LogCaptureFixture,
    token: str,
    outcome: str,
) -> None:
    shop.card(alice, token)

    with caplog.at_level("INFO"):
        response = shop.pay(cart.id, alice)

    [payment] = shop.payments(cart)
    [record] = [r for r in caplog.records if r.name == "coffer.payments"]
    assert record.levelname == "INFO"
    assert str(payment.id) in record.getMessage()
    assert record.getMessage().endswith(outcome)
    assert token not in response.text
    assert token not in caplog.text
