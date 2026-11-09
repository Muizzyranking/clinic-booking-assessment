import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    position  INTEGER PRIMARY KEY AUTOINCREMENT,
    id        TEXT NOT NULL UNIQUE,
    provider  TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    id         TEXT NOT NULL UNIQUE,
    slot_id    TEXT NOT NULL,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
    created_at TEXT NOT NULL
);

-- The database itself guarantees a slot can have only one confirmed booking.
CREATE UNIQUE INDEX IF NOT EXISTS ux_bookings_one_confirmed_per_slot
    ON bookings (slot_id) WHERE status = 'confirmed';
CREATE INDEX IF NOT EXISTS ix_bookings_email_seq ON bookings (email, seq);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key          TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    status_code  INTEGER NOT NULL,
    response     TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limit_hits (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket TEXT NOT NULL,
    hit_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hits_bucket_time ON rate_limit_hits (bucket, hit_at);
CREATE INDEX IF NOT EXISTS ix_hits_time ON rate_limit_hits (hit_at);
"""


def connect(path: str) -> sqlite3.Connection:
    # isolation_level=None -> autocommit; transactions are opened explicitly.
    conn = sqlite3.connect(
        path, timeout=30, isolation_level=None, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(SCHEMA)
    finally:
        conn.close()
    logger.info("Database ready at %s", path)


def get_db() -> Generator[sqlite3.Connection]:
    conn = connect(settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[None]:
    """
    Write transaction. BEGIN IMMEDIATE takes the write lock up front, so
    concurrent writers (threads or worker processes) are serialised and every
    check-then-write sequence inside is race free.
    """
    if conn.in_transaction:
        yield
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
