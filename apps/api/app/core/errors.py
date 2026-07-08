from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import log_json
from app.core.sanitization import mask_sensitive_data

logger = logging.getLogger("tradepilot.apps.api.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return build_error_response(
            request,
            status_code=exc.status_code,
            detail=exc.detail if isinstance(exc.detail, str) else "Request failed",
            error_code=f"http_{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return build_error_response(
            request,
            status_code=422,
            detail="Validation failed",
            error_code="validation_error",
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log_json(
            logger,
            "http.unhandled_exception",
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            method=request.method,
            error=mask_sensitive_data(str(exc)),
        )
        return build_error_response(
            request,
            status_code=500,
            detail="Internal server error",
            error_code="internal_server_error",
        )


def build_error_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    error_code: str,
    errors: list[dict] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = {
        "detail": mask_sensitive_data(detail),
        "error_code": error_code,
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if errors:
        payload["errors"] = mask_sensitive_data(jsonable_encoder(errors))
    response = JSONResponse(status_code=status_code, content=payload)
    if request_id:
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = request_id
    return response
