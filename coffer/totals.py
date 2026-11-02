"""The cart total, which the shop's existing calculation service provides."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select

from coffer.models import CartItem, Product, db


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str


class TotalCalculator(Protocol):
    def calculate(self, cart_id: UUID) -> Money | None:
        """Return what the cart costs, or None when it has no items."""
        ...


class CartItemsTotal:
    """Stand-in for the existing service: unit price times quantity, summed."""

    def calculate(self, cart_id: UUID) -> Money | None:
        row = db.session.execute(
            select(func.sum(CartItem.unit_price * CartItem.quantity), Product.currency)
            .join_from(CartItem, Product)
            .where(CartItem.cart_id == cart_id)
            # One currency per cart: a mixed cart raises MultipleResultsFound.
            .group_by(Product.currency)
        ).one_or_none()
        return None if row is None else Money(*row)
