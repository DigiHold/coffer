from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import text

from coffer import create_app
from coffer.models import Cart, User, UserPaymentMethod, db
from coffer.provider import PaymentProvider
from coffer.totals import CartItemsTotal, TotalCalculator
from tests.shop import Shop
from tests.spy_provider import SpyProvider


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database() -> None:
    command.upgrade(Config(toml_file="pyproject.toml"), "head")


@pytest.fixture
def provider() -> SpyProvider:
    return SpyProvider()


@pytest.fixture
def totals() -> TotalCalculator:
    return CartItemsTotal()


@pytest.fixture
def app(provider: PaymentProvider, totals: TotalCalculator) -> Iterator[Flask]:
    app = create_app(provider=provider, totals=totals)
    app.testing = True
    with app.app_context():
        db.session.execute(text("TRUNCATE " + ", ".join(db.metadata.tables)))
        db.session.commit()
    yield app
    with app.app_context():
        db.engine.dispose()


@pytest.fixture
def shop(app: Flask) -> Shop:
    return Shop(app)


@pytest.fixture
def alice(shop: Shop) -> User:
    return shop.user("alice")


@pytest.fixture
def cart(shop: Shop, alice: User) -> Cart:
    return shop.cart(alice)


@pytest.fixture
def card(shop: Shop, alice: User) -> UserPaymentMethod:
    return shop.card(alice)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
