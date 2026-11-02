"""Every error leaves the API in one JSON shape: {"error": {"code", "message"}}."""

from http import HTTPStatus
from typing import Any

from flask import Flask, json
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


class ApiError(Exception):
    """An expected failure, answered with its status and a stable error code."""

    def __init__(
        self, status: HTTPStatus, code: str, message: str, **details: object
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[dict[str, Any], int]:
        return _body(error.code, str(error), **error.details), error.status

    # 404, 405 and the 500 Flask sends after logging a crash. Keeps the Allow header.
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Response:
        response = error.get_response()
        code = error.name.lower().replace(" ", "_")
        response.data = json.dumps(_body(code, error.description))
        response.content_type = "application/json"
        return response


def _body(code: str, message: str | None, **details: object) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, **details}}
