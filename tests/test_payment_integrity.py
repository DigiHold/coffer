from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from coffer.models import Cart, User, UserPaymentMethod, db
from coffer.totals import CartItemsTotal, Money, TotalCalculator
from tests.shop import Shop


class CardDeletingTotal(CartItemsTotal):
    """Deletes the saved cards between the card lookup and the payment insert."""

    def calculate(self, cart_id: UUID) -> Money | None:
        db.session.execute(delete(UserPaymentMethod))
        return super().calculate(cart_id)


@pytest.fixture
def totals() -> TotalCalculator:
    return CardDeletingTotal()


def test_only_the_open_payment_index_is_answered_as_a_payment_in_progress(
    shop: Shop, alice: User, cart: Cart, card: UserPaymentMethod
) -> None:
    with pytest.raises(IntegrityError, match="payments_payment_method_id_fkey"):
        shop.pay(cart.id, alice)
