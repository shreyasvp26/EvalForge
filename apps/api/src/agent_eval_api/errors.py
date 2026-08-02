"""Translate Application / shared errors into consistent HTTP error responses.

No stack traces are returned to clients (Backend Architecture §9, REST Error Model).
"""

from __future__ import annotations

import logging
from typing import Any

from agent_eval_application.errors import (
    ApplicationLayerError,
    ApplicationValidationError,
    AuthorizationError,
    ConflictError,
    NotFoundApplicationError,
)
from agent_eval_shared.errors import AppError, InfrastructureError, ValidationError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def error_body(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    """Canonical error schema for every Control Plane failure."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def _status_for_app_error(exc: AppError) -> int:
    if isinstance(exc, AuthorizationError):
        return 403
    if isinstance(exc, NotFoundApplicationError):
        return 404
    if isinstance(exc, ConflictError):
        return 409
    if isinstance(exc, (ApplicationValidationError, ValidationError)):
        return 422
    if isinstance(exc, InfrastructureError):
        return 503
    if isinstance(exc, ApplicationLayerError):
        # DomainTranslationError and other orchestration failures
        if exc.code == "NOT_FOUND":
            return 404
        if exc.code in {"INVALID_STATE_TRANSITION", "INVARIANT_VIOLATION"}:
            return 409
        return 422
    return 400


def _body_from_app_error(exc: AppError) -> dict[str, Any]:
    return error_body(
        code=exc.code,
        message=str(exc),
        details=exc.details,
        retryable=exc.retryable,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for_app_error(exc),
            content=_body_from_app_error(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="REQUEST_VALIDATION",
                message="Request failed shape validation",
                details={"errors": exc.errors()},
                retryable=False,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        message = detail if isinstance(detail, str) else "HTTP error"
        code = "HTTP_ERROR"
        if exc.status_code == 401:
            code = "UNAUTHENTICATED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code=code, message=message, retryable=False),
        )

    @app.exception_handler(Exception)
    async def unexpected_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception in Control Plane: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_body(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                retryable=False,
            ),
        )
