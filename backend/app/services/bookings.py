import base64
import binascii
import hashlib
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database import transaction
from app.exceptions import AppException
from app.models import IdempotencyRecord
from app.rate_limit import RateLimiter, rate_limited
from app.repositories.bookings import BookingRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.slots import SlotRepository
from app.schemas import BookingCreate, BookingOut, BookingPage, ErrorOut
from app.timeutils import now_iso, parse_iso

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Failure:
    """A booking attempt that was turned away (kept so retries can replay it)."""

    status_code: int
    message: str


Outcome = BookingOut | Failure


def normalize_email(value: str | None) -> str | None:
    cleaned = (value or "").strip().lower()
    return cleaned or None


def booking_bucket(payload: BookingCreate) -> str | None:
    """Rate-limit bucket: one per email. No email (nothing to key on) -> no limit."""
    email = normalize_email(payload.email)
    return f"booking:{email}" if email else None


def _encode_cursor(seq: int) -> str:
    return base64.urlsafe_b64encode(str(seq).encode()).decode()


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error):
        raise AppException("invalid cursor", 400, "invalid_cursor") from None
    if value < 0:
        raise AppException("invalid cursor", 400, "invalid_cursor")
    return value


class BookingService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._slots = SlotRepository(conn)
        self._bookings = BookingRepository(conn)
        self._idempotency = IdempotencyRepository(conn)
        self.rate_limiter = RateLimiter(conn)

    # create
    def create(self, payload: BookingCreate, idempotency_key: str | None) -> BookingOut:
        request_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
        key = (idempotency_key or "").strip() or None

        # idempotency lookup, rate limiting,
        # validation, the booking itself and storing the outcome. Concurrent
        # requests are serialised by SQLite, so none of these steps can race.
        with transaction(self._conn):
            stored = self._idempotency.get(key) if key else None
            if stored is not None:
                outcome = self._replay(stored, request_hash)
            else:
                outcome = self._attempt(payload)
                if key:
                    self._idempotency.save(self._record(key, request_hash, outcome))

        if isinstance(outcome, Failure):
            raise AppException(outcome.message, outcome.status_code, "booking_rejected")
        return outcome

    @rate_limited(key=booking_bucket)
    def _attempt(self, payload: BookingCreate) -> Outcome:
        try:
            return self._create_booking(payload)
        except AppException as exc:
            return Failure(exc.status_code, exc.message)

    def _create_booking(self, payload: BookingCreate) -> BookingOut:
        slot_id = self._required_text(payload.slot_id, "slot_id")
        name = self._required_text(payload.name, "name")
        email = self._required_text(payload.email, "email").lower()
        if not EMAIL_PATTERN.match(email):
            raise AppException("email is not a valid address", 400, "invalid_email")

        slot = self._slots.get(slot_id)
        if slot is None:
            raise AppException("slot not found", 404, "slot_not_found")
        if parse_iso(slot.start) <= datetime.now(UTC):
            raise AppException("slot has already started", 400, "slot_started")
        if self._bookings.is_slot_booked(slot_id):
            raise AppException("slot is already booked", 409, "slot_taken")

        try:
            booking = self._bookings.create(
                slot_id=slot_id, name=name, email=email, created_at=now_iso()
            )
        except sqlite3.IntegrityError:
            # Safety net: the partial unique index rejected a second booking.
            raise AppException("slot is already booked", 409, "slot_taken") from None
        logger.info("Booking %s created for slot %s", booking.id, slot_id)
        return BookingOut.model_validate(booking)

    @staticmethod
    def _required_text(value: str | None, field: str) -> str:
        if value is None or not value.strip():
            raise AppException(
                f"{field} is required and must be a non-empty string",
                400,
                "invalid_field",
            )
        return value.strip()

    # idempotency
    @staticmethod
    def _record(key: str, request_hash: str, outcome: Outcome) -> IdempotencyRecord:
        if isinstance(outcome, Failure):
            status_code = outcome.status_code
            response = ErrorOut(error=outcome.message).model_dump_json()
        else:
            status_code = 201
            response = outcome.model_dump_json()
        return IdempotencyRecord(key, request_hash, status_code, response)

    @staticmethod
    def _replay(stored: IdempotencyRecord, request_hash: str) -> Outcome:
        if stored.request_hash != request_hash:
            raise AppException(
                "Idempotency-Key was already used with a different request body",
                422,
                "idempotency_conflict",
            )
        logger.info("Idempotent replay of key=%s -> %s", stored.key, stored.status_code)
        if stored.status_code == 201:
            return BookingOut.model_validate_json(stored.response)
        error = ErrorOut.model_validate_json(stored.response)
        return Failure(stored.status_code, error.error)

    # reads
    def get(self, booking_id: str) -> BookingOut:
        booking = self._bookings.get(booking_id)
        if booking is None:
            raise AppException("booking not found", 404, "booking_not_found")
        return BookingOut.model_validate(booking)

    def list_for_email(self, email: str, limit: int, cursor: str | None) -> BookingPage:
        normalized = normalize_email(email)
        if normalized is None:
            raise AppException("email is required", 400, "invalid_email")
        after_seq = _decode_cursor(cursor)
        found = self._bookings.list_for_email(normalized, after_seq, limit + 1)
        page = found[:limit]
        has_more = len(found) > limit
        return BookingPage(
            bookings=[BookingOut.model_validate(b) for b in page],
            next_cursor=_encode_cursor(page[-1].seq) if has_more else None,
        )

    # cancel
    def cancel(self, booking_id: str) -> BookingOut:
        with transaction(self._conn):
            booking = self._bookings.get(booking_id)
            if booking is None:
                raise AppException("booking not found", 404, "booking_not_found")
            if booking.status == "cancelled":
                raise AppException(
                    "booking is already cancelled", 409, "already_cancelled"
                )
            self._bookings.mark_cancelled(booking_id)
            updated = self._bookings.get(booking_id)
        if updated is None:  # pragma: no cover
            raise RuntimeError("booking vanished after update")
        logger.info("Booking %s cancelled, slot %s freed", booking_id, booking.slot_id)
        return BookingOut.model_validate(updated)
