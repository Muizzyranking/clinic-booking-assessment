import sqlite3
from collections.abc import Sequence

from app.models import Slot

_SELECT = """
SELECT s.id, s.provider, s.starts_at AS start, s.ends_at AS "end",
       NOT EXISTS (
           SELECT 1 FROM bookings b
           WHERE b.slot_id = s.id AND b.status = 'confirmed'
       ) AS available
FROM slots s
"""


class SlotRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def clear(self) -> None:
        self._conn.execute("DELETE FROM slots")

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS total FROM slots").fetchone()
        return int(row["total"])

    def insert_many(self, slots: Sequence[Slot]) -> None:
        self._conn.executemany(
            "INSERT INTO slots (id, provider, starts_at, ends_at) VALUES (?, ?, ?, ?)",
            [(s.id, s.provider, s.start, s.end) for s in slots],
        )

    def list(self, provider: str | None = None) -> list[Slot]:
        query = _SELECT
        params: tuple[str, ...] = ()
        if provider is not None:
            query += " WHERE s.provider = ?"
            params = (provider,)
        query += " ORDER BY s.position"
        return [Slot.from_row(row) for row in self._conn.execute(query, params)]

    def get(self, slot_id: str) -> Slot | None:
        row = self._conn.execute(_SELECT + " WHERE s.id = ?", (slot_id,)).fetchone()
        return Slot.from_row(row) if row else None
