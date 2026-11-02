from decimal import Decimal
from typing import Any

from flask import Flask
from sqlalchemy import Executable, select

from coffer.models import (
    Base,
    Cart,
    CartItem,
    Payment,
    Product,
    User,
    UserPaymentMethod,
    db,
)


class Shop:
    """Builds rows and reads them back, each in its own app context."""

    def __init__(self, app: Flask) -> None:
        self.app = app

    def add(self, *rows: Base) -> None:
        with self.app.app_context():
            db.session.add_all(rows)
            db.session.commit()

    def execute(self, statement: Executable) -> None:
        with self.app.app_context():
            db.session.execute(statement)
            db.session.commit()

    def user(self, name: str) -> User:
        user = User(email=f"{name}@example.com", name=name.title())
        self.add(user)
        return user

    def cart(
        self,
        user: User,
        items: tuple[tuple[str, int], ...] = (("45.00", 1), ("12.50", 2)),
        status: str = "active",
        currency: str = "USD",
    ) -> Cart:
        """The default items are those of the task's sample cart: 70.00 in total."""
        cart = Cart(user_id=user.id, status=status)
        self.add(cart)
        for unit_price, quantity in items:
            product = Product(name="Mug", price=Decimal(unit_price), currency=currency)
            self.add(product)
            self.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=Decimal(unit_price),
                )
            )
        return cart

    def card(
        self, user: User, token: str = "tok_test_visa", *, is_default: bool = True
    ) -> UserPaymentMethod:
        card = UserPaymentMethod(
            user_id=user.id, provider_token=token, is_default=is_default
        )
        self.add(card)
        return card

    def payment(self, cart: Cart, card: UserPaymentMethod, **columns: Any) -> Payment:
        payment = Payment(
            **{
                "cart_id": cart.id,
                "payment_method_id": card.id,
                "amount": Decimal("70.00"),
                "currency": "USD",
                **columns,
            }
        )
        self.add(payment)
        return payment

    def payments(self, cart: Cart) -> list[Payment]:
        with self.app.app_context():
            return list(
                db.session.scalars(select(Payment).where(Payment.cart_id == cart.id))
            )
