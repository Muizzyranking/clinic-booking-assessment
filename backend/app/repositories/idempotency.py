import sqlite3

from app.models import IdempotencyRecord
from app.timeutils import now_iso


class IdempotencyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> IdempotencyRecord | None:
        row = self._conn.execute(
            "SELECT key, request_hash, status_code, response "
            "FROM idempotency_keys WHERE key = ?",
            (key,),
        ).fetchone()
        return IdempotencyRecord.from_row(row) if row else None

    def save(self, record: IdempotencyRecord) -> None:
        self._conn.execute(
            "INSERT INTO idempotency_keys "
            "(key, request_hash, status_code, response, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                record.key,
                record.request_hash,
                record.status_code,
                record.response,
                now_iso(),
            ),
        )

    def clear(self) -> None:
        self._conn.execute("DELETE FROM idempotency_keys")
