"""Coffer: the payment endpoint of the online shop."""

import logging

from flask import Flask

from coffer.auth import issue_token_command
from coffer.config import load_config
from coffer.errors import register_error_handlers
from coffer.models import db
from coffer.provider import MockPaymentProvider, PaymentProvider
from coffer.routes import blueprint
from coffer.totals import CartItemsTotal, TotalCalculator


def create_app(
    provider: PaymentProvider | None = None, totals: TotalCalculator | None = None
) -> Flask:
    """Build the app. Tests inject their own provider and total calculator."""
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    # Flask's logger is "coffer", the parent of every module logger here.
    app.logger.setLevel(logging.INFO)
    app.extensions["payment_provider"] = provider or MockPaymentProvider()
    app.extensions["total_calculator"] = totals or CartItemsTotal()
    db.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    app.cli.add_command(issue_token_command)
    return app
