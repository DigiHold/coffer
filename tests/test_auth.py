import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from flask import Flask

from coffer.auth import authenticated_user_id, issue_token
from coffer.errors import ApiError
from coffer.models import User

FUTURE = datetime.now(UTC) + timedelta(hours=1)
PAST = datetime.now(UTC) - timedelta(seconds=1)


def authenticate(app: Flask, authorization: str | None) -> UUID:
    headers = {"Authorization": authorization} if authorization else {}
    with app.test_request_context(headers=headers):
        return authenticated_user_id()


def bearer(claims: dict[str, object], key: str, algorithm: str = "HS256") -> str:
    return "Bearer " + jwt.encode(claims, key, algorithm=algorithm)


def test_accepts_a_token_issued_to_an_existing_user(app: Flask, alice: User) -> None:
    token = issue_token(alice.id, app.config["JWT_SECRET"])

    assert authenticate(app, f"Bearer {token}") == alice.id


def test_issues_tokens_valid_for_one_hour(app: Flask, alice: User) -> None:
    secret = app.config["JWT_SECRET"]

    claims = jwt.decode(issue_token(alice.id, secret), secret, algorithms=["HS256"])

    assert claims["sub"] == str(alice.id)
    assert 3590 < claims["exp"] - time.time() <= 3600


# Each case builds an Authorization header from Alice's id and the signing key.
REJECTED: dict[str, Callable[[str, str], str | None]] = {
    "no header": lambda user_id, key: None,
    "basic scheme": lambda user_id, key: "Basic YWxpY2U6cGFzc3dvcmQ=",
    "bearer without token": lambda user_id, key: "Bearer",
    "not a jwt": lambda user_id, key: "Bearer not-a-jwt",
    "other key": lambda user_id, key: bearer(
        {"sub": user_id, "exp": FUTURE}, "another-signing-key-of-32-bytes!"
    ),
    "unsigned": lambda user_id, key: bearer(
        {"sub": user_id, "exp": FUTURE}, "", algorithm="none"
    ),
    "expired": lambda user_id, key: bearer({"sub": user_id, "exp": PAST}, key),
    "no expiry": lambda user_id, key: bearer({"sub": user_id}, key),
    "no subject": lambda user_id, key: bearer({"exp": FUTURE}, key),
    "subject not a user id": lambda user_id, key: bearer(
        {"sub": "alice", "exp": FUTURE}, key
    ),
    "unknown user": lambda user_id, key: bearer(
        {"sub": str(uuid4()), "exp": FUTURE}, key
    ),
}


@pytest.mark.parametrize("header", REJECTED.values(), ids=REJECTED.keys())
def test_rejects_missing_or_invalid_credentials(
    app: Flask, alice: User, header: Callable[[str, str], str | None]
) -> None:
    with pytest.raises(ApiError) as error:
        authenticate(app, header(str(alice.id), app.config["JWT_SECRET"]))

    assert error.value.code == "unauthorized"


def test_issue_token_command_prints_a_token_for_the_user(
    app: Flask, alice: User
) -> None:
    result = app.test_cli_runner().invoke(args=["issue-token", "alice@example.com"])

    assert result.exit_code == 0
    assert authenticate(app, f"Bearer {result.output.strip()}") == alice.id


def test_issue_token_command_rejects_an_unknown_email(app: Flask) -> None:
    result = app.test_cli_runner().invoke(args=["issue-token", "nobody@example.com"])

    assert result.exit_code == 1
    assert "nobody@example.com" in result.output
