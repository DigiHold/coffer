"""Mappings of the columns the code uses. The migrations own the schema."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, FetchedValue, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Values stay loaded after a commit, so reading one never opens a transaction.
db = SQLAlchemy(model_class=Base, session_options={"expire_on_commit": False})


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    email: Mapped[str]
    name: Mapped[str]


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    name: Mapped[str]
    price: Mapped[Decimal]
    currency: Mapped[str]


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(server_default=FetchedValue())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue(), onupdate=func.now()
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal]


class UserPaymentMethod(Base):
    __tablename__ = "user_payment_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    provider_token: Mapped[str]
    is_default: Mapped[bool] = mapped_column(server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id"))
    payment_method_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_payment_methods.id")
    )
    amount: Mapped[Decimal]
    currency: Mapped[str]
    status: Mapped[str] = mapped_column(server_default=FetchedValue())
    provider_reference: Mapped[str | None]
    failure_reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue(), onupdate=func.now()
    )
