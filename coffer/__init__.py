"""Coffer: the payment endpoint of the online shop."""

from flask import Flask

from coffer.config import load_config
from coffer.models import db


def create_app() -> Flask:
    """Build the app from the settings in the environment."""
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    db.init_app(app)
    return app
