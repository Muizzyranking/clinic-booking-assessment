import sqlite3
import uuid

from app.models import Booking

_COLUMNS = "seq, id, slot_id, name, email, status, created_at"


class BookingRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self, *, slot_id: str, name: str, email: str, created_at: str
    ) -> Booking:
        booking_id = uuid.uuid4().hex
        self._conn.execute(
            "INSERT INTO bookings (id, slot_id, name, email, status, created_at) "
            "VALUES (?, ?, ?, ?, 'confirmed', ?)",
            (booking_id, slot_id, name, email, created_at),
        )
        booking = self.get(booking_id)
        if booking is None:  # pragma: no cover - cannot happen inside a transaction
            raise RuntimeError("booking vanished after insert")
        return booking

    def get(self, booking_id: str) -> Booking | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM bookings WHERE id = ?", (booking_id,)
        ).fetchone()
        return Booking.from_row(row) if row else None

    def is_slot_booked(self, slot_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM bookings WHERE slot_id = ? AND status = 'confirmed'",
            (slot_id,),
        ).fetchone()
        return row is not None

    def mark_cancelled(self, booking_id: str) -> None:
        self._conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )

    def list_for_email(self, email: str, after_seq: int, limit: int) -> list[Booking]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM bookings "
            "WHERE email = ? AND seq > ? ORDER BY seq LIMIT ?",
            (email, after_seq, limit),
        )
        return [Booking.from_row(row) for row in rows]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM bookings")
