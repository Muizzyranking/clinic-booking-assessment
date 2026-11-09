import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorOut

logger = logging.getLogger(__name__)

_NON_FIELD_LOCS = {"body", "query", "path", "header", "cookie"}


class AppException(Exception):  # noqa: N818
    """The one exception the application raises for expected failures.

    message     -> human readable text returned as {"error": message}
    status_code -> HTTP status of the response
    error       -> short machine code, used for logging
    headers     -> optional response headers (e.g. Retry-After)
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error: str = "error",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error = error
        self.headers = headers


def error_response(
    message: str, status_code: int, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorOut(error=message).model_dump(),
        headers=headers,
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        "%s %s -> %s (%s): %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.error,
        exc.message,
    )
    return error_response(exc.message, exc.status_code, exc.headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = ".".join(
        str(part) for part in first.get("loc", ()) if part not in _NON_FIELD_LOCS
    )
    detail = str(first.get("msg", "invalid request"))
    message = f"{location}: {detail}" if location else detail
    logger.warning(
        "%s %s -> 400 (validation): %s", request.method, request.url.path, message
    )
    return error_response(message, 400)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "request failed"
    return error_response(
        message.lower(), exc.status_code, getattr(exc, "headers", None)
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response("internal server error", 500)
