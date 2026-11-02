from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from sqlalchemy import text

from coffer import create_app
from coffer.models import Cart, User, UserPaymentMethod, db
from tests.shop import Shop


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database() -> None:
    command.upgrade(Config(toml_file="pyproject.toml"), "head")


@pytest.fixture
def app() -> Iterator[Flask]:
    app = create_app()
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
