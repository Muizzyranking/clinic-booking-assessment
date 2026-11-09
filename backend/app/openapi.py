from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas import ErrorOut

DESCRIPTION = """
Appointment booking for a clinic. Every request needs the `X-API-Key` header.
"""

TAGS = [
    {"name": "slots", "description": "Clinic slots. `POST /reset` replaces them all."},
    {"name": "bookings", "description": "Book, look up, list and cancel appointments."},
    {
        "name": "demo data",
        "description": "Random doctors, slots and bookings for demos.",
    },
]

ERROR_TEXT: dict[int, str] = {
    400: "Missing or invalid input, or the slot has already started",
    401: "Missing or wrong `X-API-Key`",
    404: "Not found",
    409: "Conflict (slot already booked, or booking already cancelled)",
    422: "`Idempotency-Key` was already used with a different body",
    429: "Too many attempts for this email; wait `Retry-After` seconds",
}


def errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Documented error responses, all shaped like ErrorOut."""
    documented: dict[int | str, dict[str, Any]] = {}
    for code in codes:
        entry: dict[str, Any] = {"model": ErrorOut, "description": ERROR_TEXT[code]}
        if code == 429:
            entry["headers"] = {
                "Retry-After": {
                    "description": "Seconds to wait",
                    "schema": {"type": "integer"},
                }
            }
        documented[code] = entry
    return documented


def install_openapi(app: FastAPI) -> None:
    """Build the schema once, dropping FastAPI's default 422 (validation errors
    are returned as 400 + ErrorOut by our handler, so the default is wrong)."""

    def build() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers or None,
        )
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                response = operation.get("responses", {}).get("422")
                if response and "HTTPValidationError" in str(response):
                    del operation["responses"]["422"]
        for name in ("HTTPValidationError", "ValidationError"):
            schema.get("components", {}).get("schemas", {}).pop(name, None)
        app.openapi_schema = schema
        return schema

    app.openapi = build  # type: ignore[method-assign]
