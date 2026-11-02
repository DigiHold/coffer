"""Settings read from the environment once, when the app starts."""

import os
from typing import Any

# RFC 7518 section 3.2: an HS256 key must be at least as long as the SHA-256 output.
MIN_JWT_SECRET_BYTES = 32


def load_config() -> dict[str, Any]:
    """Return the Flask settings, failing fast when one is missing or unsafe."""
    jwt_secret = _required("JWT_SECRET")
    if len(jwt_secret.encode()) < MIN_JWT_SECRET_BYTES:
        raise RuntimeError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes")
    return {
        "SQLALCHEMY_DATABASE_URI": _required("DATABASE_URL"),
        "JWT_SECRET": jwt_secret,
    }


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value
