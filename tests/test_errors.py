from http import HTTPStatus
from typing import NoReturn
from uuid import uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient

from tests.shop import assert_error


def test_hides_an_unexpected_error_behind_a_json_500(
    app: Flask, client: FlaskClient, caplog: pytest.LogCaptureFixture
) -> None:
    def crash() -> NoReturn:
        raise RuntimeError("internal detail")

    app.add_url_rule("/crash", view_func=crash)
    app.testing = False

    response = client.get("/crash")

    assert_error(response, HTTPStatus.INTERNAL_SERVER_ERROR, "internal_server_error")
    assert "internal detail" not in response.text
    assert "internal detail" in caplog.text


def test_answers_a_wrong_method_with_a_json_405_that_lists_the_allowed_ones(
    client: FlaskClient,
) -> None:
    response = client.get(f"/carts/{uuid4()}/payments")

    assert_error(response, HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")
    assert "POST" in response.headers["Allow"]
