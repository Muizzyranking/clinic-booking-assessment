import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database import connect, init_db
from app.exceptions import AppException
from app.models import Booking, BookingStatus, Slot
from app.rate_limit import RateLimiter, rate_limited


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    path = str(tmp_path / "unit.db")
    init_db(path)
    connection = connect(path)
    yield connection
    connection.close()


def test_model_from_row_converts_enum_and_bool(conn: sqlite3.Connection) -> None:
    booking_row = conn.execute(
        "SELECT 7 AS seq, 'b1' AS id, 's1' AS slot_id, 'Ada' AS name, "
        "'a@b.co' AS email, 'cancelled' AS status, 'now' AS created_at"
    ).fetchone()
    booking = Booking.from_row(booking_row)
    assert booking.status is BookingStatus.CANCELLED
    assert booking.seq == 7

    slot_row = conn.execute(
        "SELECT 's1' AS id, 'Dr Chioma Okafor' AS provider, "
        "'a' AS start, 'b' AS \"end\", "
        "0 AS available"
    ).fetchone()
    assert Slot.from_row(slot_row).available is False


class Thing:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.rate_limiter = RateLimiter(conn)
        self.runs = 0

    @rate_limited(
        key=lambda _self, who: f"thing:{who}" if who else None, limit=2, window=60
    )
    def act(self, who: str | None) -> int:
        self.runs += 1
        return self.runs


def test_decorator_blocks_after_limit_and_skips_the_call(
    conn: sqlite3.Connection,
) -> None:
    thing = Thing(conn)
    assert thing.act("ada") == 1
    assert thing.act("ada") == 2
    with pytest.raises(AppException) as excinfo:
        thing.act("ada")
    assert excinfo.value.status_code == 429
    assert excinfo.value.headers is not None
    assert 1 <= int(excinfo.value.headers["Retry-After"]) <= 60
    assert thing.runs == 2  # the limited call never ran


def test_decorator_buckets_are_independent_and_none_skips(
    conn: sqlite3.Connection,
) -> None:
    thing = Thing(conn)
    thing.act("ada")
    thing.act("ada")
    assert thing.act("bola") == 3
    for _ in range(10):
        thing.act(None)  # no bucket -> never limited


def test_helper_can_be_called_directly(conn: sqlite3.Connection) -> None:
    limiter = RateLimiter(conn)
    limiter.hit("login:1.2.3.4", limit=1, window=60)
    with pytest.raises(AppException):
        limiter.hit("login:1.2.3.4", limit=1, window=60)
    limiter.hit("login:5.6.7.8", limit=1, window=60)
