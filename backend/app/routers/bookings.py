from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.config import settings
from app.dependencies import BookingServiceDep, require_api_key
from app.openapi import errors
from app.schemas import BookingCreate, BookingOut, BookingPage

router = APIRouter(
    dependencies=[Depends(require_api_key)],
    tags=["bookings"],
    responses=errors(401),
)


@router.post(
    "/bookings",
    response_model=BookingOut,
    status_code=201,
    summary="Book a slot",
    description=(
        "Returns 201 with the booking, status `confirmed`. `name` and `email` are "
        "trimmed and the email is stored in lower case.\n\n"
        "Send an `Idempotency-Key` header to make retries safe: the same key with the "
        "same body returns the same response and never creates a second booking.\n\n"
        "At most 5 attempts per email per minute, failed attempts included."
    ),
    responses=errors(400, 404, 409, 422, 429),
)
def create_booking(
    payload: BookingCreate,
    service: BookingServiceDep,
    idempotency_key: Annotated[
        str | None,
        Header(
            description=(
                "Makes retries safe. Reusing it with a different body gives 422."
            )
        ),
    ] = None,
) -> BookingOut:
    return service.create(payload, idempotency_key)


@router.get(
    "/bookings",
    response_model=BookingPage,
    summary="List a person's bookings",
    description=(
        "That person's bookings, oldest first; the email match ignores case. "
        "Pass `next_cursor` back as `cursor` for the next page. The last page has "
        "`next_cursor: null`."
    ),
    responses=errors(400),
)
def list_bookings(
    service: BookingServiceDep,
    email: Annotated[str, Query(description="Whose bookings to list")],
    limit: Annotated[
        int, Query(ge=1, le=settings.max_page_size, description="Page size")
    ] = settings.default_page_size,
    cursor: Annotated[
        str | None, Query(description="`next_cursor` from the previous page")
    ] = None,
) -> BookingPage:
    return service.list_for_email(email, limit, cursor)


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingOut,
    summary="Look up a booking",
    responses=errors(404),
)
def get_booking(booking_id: str, service: BookingServiceDep) -> BookingOut:
    return service.get(booking_id)


@router.delete(
    "/bookings/{booking_id}",
    response_model=BookingOut,
    summary="Cancel a booking",
    description="Sets the status to `cancelled` and frees the slot.",
    responses=errors(404, 409),
)
def cancel_booking(booking_id: str, service: BookingServiceDep) -> BookingOut:
    return service.cancel(booking_id)
