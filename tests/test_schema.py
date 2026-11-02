"""The payments table enforces its rules itself, whatever code writes to it."""

from decimal import Decimal
from typing import Any

import psycopg
import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from coffer.models import Cart, User, UserPaymentMethod
from tests.shop import Shop


def violated_constraint(error: pytest.ExceptionInfo[IntegrityError]) -> str | None:
    assert isinstance(error.value.orig, psycopg.Error)
    return error.value.orig.diag.constraint_name


@pytest.mark.parametrize(
    "open_payment",
    [{"status": "pending"}, {"status": "succeeded", "provider_reference": "ch_1"}],
    ids=["pending", "succeeded"],
)
def test_a_cart_has_at_most_one_open_payment(
    shop: Shop, cart: Cart, card: UserPaymentMethod, open_payment: dict[str, Any]
) -> None:
    shop.payment(cart, card, **open_payment)

    with pytest.raises(IntegrityError) as error:
        shop.payment(cart, card)

    assert violated_constraint(error) == "uq_payments_cart_open"


def test_failed_attempts_do_not_block_a_new_payment(
    shop: Shop, cart: Cart, card: UserPaymentMethod
) -> None:
    shop.payment(cart, card, status="failed", failure_reason="card_declined")
    shop.payment(cart, card, status="failed", failure_reason="provider_unavailable")
    shop.payment(cart, card)

    statuses = sorted(payment.status for payment in shop.payments(cart))
    assert statuses == ["failed", "failed", "pending"]


@pytest.mark.parametrize(
    ("columns", "constraint"),
    [
        ({"amount": Decimal("0.00")}, "payments_amount_check"),
        ({"amount": Decimal("-1.00")}, "payments_amount_check"),
        ({"status": "refunded"}, "payments_status_check"),
        ({"status": "succeeded"}, "payments_succeeded_has_reference"),
        ({"status": "failed"}, "payments_reason_only_when_failed"),
        ({"failure_reason": "card_declined"}, "payments_reason_only_when_failed"),
    ],
    ids=[
        "zero",
        "negative",
        "unknown-status",
        "succeeded-without-reference",
        "failed-without-reason",
        "pending-with-reason",
    ],
)
def test_rejects_an_inconsistent_payment(
    shop: Shop,
    cart: Cart,
    card: UserPaymentMethod,
    columns: dict[str, Any],
    constraint: str,
) -> None:
    with pytest.raises(IntegrityError) as error:
        shop.payment(cart, card, **columns)

    assert violated_constraint(error) == constraint


def test_a_provider_reference_belongs_to_one_payment(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod
) -> None:
    shop.payment(cart, card, status="succeeded", provider_reference="ch_1")

    with pytest.raises(IntegrityError) as error:
        shop.payment(
            shop.cart(alice), card, status="succeeded", provider_reference="ch_1"
        )

    assert violated_constraint(error) == "payments_provider_reference_key"


def test_a_cart_with_payments_cannot_be_deleted(
    shop: Shop, cart: Cart, card: UserPaymentMethod
) -> None:
    shop.payment(cart, card)

    with pytest.raises(IntegrityError) as error:
        shop.execute(delete(Cart).where(Cart.id == cart.id))

    assert violated_constraint(error) == "payments_cart_id_fkey"


def test_a_card_with_payments_cannot_be_deleted(
    shop: Shop, cart: Cart, card: UserPaymentMethod
) -> None:
    shop.payment(cart, card)

    with pytest.raises(IntegrityError) as error:
        shop.execute(delete(UserPaymentMethod).where(UserPaymentMethod.id == card.id))

    assert violated_constraint(error) == "payments_payment_method_id_fkey"
