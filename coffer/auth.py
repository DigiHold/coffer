"""Bearer token authentication: an HS256 JWT whose subject is the user id."""

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from uuid import UUID

import click
import jwt
from flask import current_app, request
from flask.cli import with_appcontext
from sqlalchemy import select

from coffer.errors import ApiError
from coffer.models import User, db

ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(hours=1)


def issue_token(user_id: UUID, secret: str) -> str:
    expires_at = datetime.now(UTC) + TOKEN_LIFETIME
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at}, secret, algorithm=ALGORITHM
    )


def authenticated_user_id() -> UUID:
    """Return the id of the existing user the request's bearer token names."""
    credentials = request.authorization
    if credentials is None or credentials.type != "bearer" or not credentials.token:
        raise _unauthorized()
    try:
        claims = jwt.decode(
            credentials.token,
            current_app.config["JWT_SECRET"],
            # Pinned, so a token cannot pick its own algorithm, "none" included.
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        user_id = UUID(claims["sub"])
    except jwt.InvalidTokenError, ValueError:
        raise _unauthorized() from None
    if db.session.get(User, user_id) is None:
        raise _unauthorized()
    return user_id


def _unauthorized() -> ApiError:
    return ApiError(
        HTTPStatus.UNAUTHORIZED, "unauthorized", "Missing or invalid bearer token."
    )


@click.command("issue-token")
@click.argument("email")
@with_appcontext
def issue_token_command(email: str) -> None:
    """Print a one hour bearer token for the user with this email."""
    user = db.session.scalar(select(User).where(User.email == email))
    if user is None:
        raise click.ClickException(f"No user with the email {email}.")
    click.echo(issue_token(user.id, current_app.config["JWT_SECRET"]))
