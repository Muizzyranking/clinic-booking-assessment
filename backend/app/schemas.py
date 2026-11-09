from pydantic import BaseModel, ConfigDict

from app.models import BookingStatus


class SlotIn(BaseModel):
    id: str
    provider: str
    start: str
    end: str


class ResetRequest(BaseModel):
    slots: list[SlotIn]


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    start: str
    end: str
    available: bool


class SlotsOut(BaseModel):
    slots: list[SlotOut]


class BookingCreate(BaseModel):
    """Deliberately lenient (every field optional): emptiness and format are
    checked in the service, so invalid attempts still count toward the rate
    limit and every bad input yields the same 400 error shape."""

    model_config = ConfigDict(extra="ignore")

    slot_id: str | None = None
    name: str | None = None
    email: str | None = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slot_id: str
    name: str
    email: str
    status: BookingStatus
    created_at: str


class BookingPage(BaseModel):
    bookings: list[BookingOut]
    next_cursor: str | None


class ErrorOut(BaseModel):
    error: str
