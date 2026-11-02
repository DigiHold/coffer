from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.exc import MultipleResultsFound

from coffer.models import Product, User
from coffer.totals import CartItemsTotal, Money
from tests.shop import Shop


def total(shop: Shop, cart_id: UUID) -> Money | None:
    with shop.app.app_context():
        return CartItemsTotal().calculate(cart_id)


def test_sums_quantity_times_unit_price(shop: Shop, alice: User) -> None:
    cart = shop.cart(alice, items=(("45.00", 1), ("12.50", 2)), currency="EUR")

    assert total(shop, cart.id) == Money(Decimal("70.00"), "EUR")


def test_keeps_the_price_the_item_was_added_at(shop: Shop, alice: User) -> None:
    cart = shop.cart(alice)
    shop.execute(update(Product).values(price=Decimal("99.00")))

    assert total(shop, cart.id) == Money(Decimal("70.00"), "USD")


def test_has_no_total_for_an_empty_cart(shop: Shop, alice: User) -> None:
    assert total(shop, shop.cart(alice, items=()).id) is None


def test_refuses_a_cart_that_mixes_currencies(shop: Shop, alice: User) -> None:
    cart = shop.cart(alice)
    shop.execute(update(Product).where(Product.price == 45).values(currency="EUR"))

    with pytest.raises(MultipleResultsFound):
        total(shop, cart.id)
