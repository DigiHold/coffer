"""Starting the payment of a cart, so that a card is never charged twice."""

import logging
from http import HTTPStatus
from typing import NoReturn
from uuid import UUID

import psycopg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from coffer.errors import ApiError
from coffer.models import Cart, Payment, UserPaymentMethod, db
from coffer.provider import (
    CardDeclinedError,
    PaymentProvider,
    ProviderUnavailableError,
)
from coffer.totals import TotalCalculator

log = logging.getLogger(__name__)

# Migration 0002: at most one pending or succeeded payment per cart.
OPEN_PAYMENT_INDEX = "uq_payments_cart_open"


def start_payment(
    user_id: UUID, cart_id: UUID, provider: PaymentProvider, totals: TotalCalculator
) -> Payment:
    """Charge the user's default card for the cart, then check the cart out."""
    # 1. Commit a pending payment: the unique index lets one request per cart in.
    cart = _active_cart(user_id, cart_id)
    card = _default_card(user_id)
    total = totals.calculate(cart.id)
    if total is None or total.amount <= 0:
        raise ApiError(
            HTTPStatus.UNPROCESSABLE_CONTENT,
            "nothing_to_pay",
            "The cart has nothing to pay.",
        )
    payment = Payment(
        cart_id=cart.id,
        payment_method_id=card.id,
        amount=total.amount,
        currency=total.currency,
    )
    _commit_pending(payment)

    # 2. Charge with no transaction open, so a slow provider holds no lock.
    try:
        reference = provider.charge(
            card.provider_token,
            payment.amount,
            payment.currency,
            idempotency_key=str(payment.id),
        )
    except CardDeclinedError:
        _fail_payment(
            payment,
            HTTPStatus.PAYMENT_REQUIRED,
            "card_declined",
            "The card was declined.",
        )
    except ProviderUnavailableError:
        _fail_payment(
            payment,
            HTTPStatus.BAD_GATEWAY,
            "provider_unavailable",
            "The payment provider is unavailable and charged nothing. Try again later.",
        )

    # 3. One commit records the success and checks the cart out.
    payment.status = "succeeded"
    payment.provider_reference = reference
    cart.status = "checked_out"
    _commit_and_log(payment)
    return payment


def _active_cart(user_id: UUID, cart_id: UUID) -> Cart:
    cart = db.session.scalar(
        select(Cart).where(Cart.id == cart_id, Cart.user_id == user_id)
    )
    if cart is None:
        # Another user's cart answers like a missing one, so ids cannot be probed.
        raise ApiError(HTTPStatus.NOT_FOUND, "cart_not_found", "Cart not found.")
    if cart.status != "active":
        raise ApiError(
            HTTPStatus.CONFLICT, "cart_not_active", "Only an active cart can be paid."
        )
    return cart


def _default_card(user_id: UUID) -> UserPaymentMethod:
    # Nothing in the base schema stops two defaults, so the newest one wins.
    card = db.session.scalar(
        select(UserPaymentMethod)
        .where(UserPaymentMethod.user_id == user_id, UserPaymentMethod.is_default)
        .order_by(UserPaymentMethod.created_at.desc(), UserPaymentMethod.id.desc())
        .limit(1)
    )
    if card is None:
        raise ApiError(
            HTTPStatus.UNPROCESSABLE_CONTENT,
            "no_payment_method",
            "Save a default card before paying.",
        )
    return card


def _commit_pending(payment: Payment) -> None:
    db.session.add(payment)
    try:
        db.session.commit()
    except IntegrityError as error:
        if (
            isinstance(error.orig, psycopg.errors.UniqueViolation)
            and error.orig.diag.constraint_name == OPEN_PAYMENT_INDEX
        ):
            raise ApiError(
                HTTPStatus.CONFLICT,
                "payment_in_progress",
                "A payment for this cart is already in progress.",
            ) from None
        raise


def _fail_payment(
    payment: Payment, status: HTTPStatus, code: str, message: str
) -> NoReturn:
    """Record the failed attempt, which frees the cart, and answer with the error."""
    payment.status = "failed"
    payment.failure_reason = code
    _commit_and_log(payment)
    raise ApiError(status, code, message, payment_id=str(payment.id)) from None


def _commit_and_log(payment: Payment) -> None:
    db.session.commit()
    log.info(
        "Payment %s for cart %s: %s",
        payment.id,
        payment.cart_id,
        payment.failure_reason or payment.status,
    )
