"""HTTP layer: authenticate, hand over to the payment service, answer in JSON."""

from http import HTTPStatus
from typing import Any
from uuid import UUID

from flask import Blueprint, current_app

from coffer.auth import authenticated_user_id
from coffer.payments import start_payment

blueprint = Blueprint("payments", __name__)


@blueprint.post("/carts/<uuid:cart_id>/payments")
def create_payment(cart_id: UUID) -> tuple[dict[str, Any], HTTPStatus]:
    payment = start_payment(
        authenticated_user_id(),
        cart_id,
        provider=current_app.extensions["payment_provider"],
        totals=current_app.extensions["total_calculator"],
    )
    return {
        "id": str(payment.id),
        "cart_id": str(payment.cart_id),
        "status": payment.status,
        # A string, so that no client reads money as a float.
        "amount": str(payment.amount),
        "currency": payment.currency,
        "created_at": payment.created_at.isoformat(),
    }, HTTPStatus.CREATED
