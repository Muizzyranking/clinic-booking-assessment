import secrets
import sqlite3
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.config import settings
from app.database import get_db
from app.exceptions import AppException
from app.services.bookings import BookingService
from app.services.slots import SlotService

DbConn = Annotated[sqlite3.Connection, Depends(get_db)]

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="The clinic API key. Sent on every request.",
)


def require_api_key(
    x_api_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    expected = settings.api_key.encode()
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), expected):
        raise AppException("missing or invalid API key", 401, "unauthorized")


def get_slot_service(conn: DbConn) -> SlotService:
    return SlotService(conn)


def get_booking_service(conn: DbConn) -> BookingService:
    return BookingService(conn)


SlotServiceDep = Annotated[SlotService, Depends(get_slot_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
