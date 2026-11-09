import logging
import sqlite3
from collections.abc import Sequence

from app.database import transaction
from app.exceptions import AppException
from app.models import Slot
from app.repositories.bookings import BookingRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.rate_limits import RateLimitRepository
from app.repositories.slots import SlotRepository
from app.schemas import ResetRequest, SlotIn, SlotOut, SlotsOut
from app.seed import seed_database
from app.timeutils import parse_iso

logger = logging.getLogger(__name__)


class SlotService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._slots = SlotRepository(conn)
        self._bookings = BookingRepository(conn)
        self._idempotency = IdempotencyRepository(conn)
        self._rate_limits = RateLimitRepository(conn)

    def list_slots(self, provider: str | None) -> SlotsOut:
        return SlotsOut(
            slots=[SlotOut.model_validate(slot) for slot in self._slots.list(provider)]
        )

    def reset(self, payload: ResetRequest) -> SlotsOut:
        self._validate(payload.slots)
        slots = [
            Slot(id=s.id.strip(), provider=s.provider, start=s.start, end=s.end)
            for s in payload.slots
        ]
        with transaction(self._conn):
            self._slots.clear()
            self._bookings.clear()
            self._idempotency.clear()
            self._rate_limits.clear()
            self._slots.insert_many(slots)
        logger.info("Reset: %d slots loaded, all other state cleared", len(slots))
        return self.list_slots(None)

    def seed(self) -> SlotsOut:
        """Replace everything with freshly generated random demo data."""
        seed_database(self._conn)
        return self.list_slots(None)

    @staticmethod
    def _validate(slots: Sequence[SlotIn]) -> None:
        seen: set[str] = set()
        for slot in slots:
            slot_id = slot.id.strip()
            if not slot_id or not slot.provider.strip():
                raise AppException(
                    "each slot needs a non-empty id and provider", 400, "invalid_slot"
                )
            if slot_id in seen:
                raise AppException(f"duplicate slot id: {slot_id}", 400, "invalid_slot")
            seen.add(slot_id)
            try:
                start, end = parse_iso(slot.start), parse_iso(slot.end)
            except ValueError:
                raise AppException(
                    f"slot {slot_id}: start and end must be ISO-8601 timestamps",
                    400,
                    "invalid_slot",
                ) from None
            if end <= start:
                raise AppException(
                    f"slot {slot_id}: end must be after start", 400, "invalid_slot"
                )
