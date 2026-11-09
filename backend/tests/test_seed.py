import random
import sqlite3
from collections import Counter
from collections.abc import Iterator
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import connect, init_db
from app.seed import (
    FIRST_NAMES,
    LAST_NAMES,
    generate_plan,
    seed_database,
    seed_if_empty,
)
from app.timeutils import parse_iso
from tests.conftest import API_KEY

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    path = str(tmp_path / "seed.db")
    init_db(path)
    connection = connect(path)
    yield connection
    connection.close()


def all_text(plan) -> list[str]:
    texts = list(plan.providers)
    texts += [
        value
        for slot in plan.slots
        for value in asdict(slot).values()
        if isinstance(value, str)
    ]
    texts += [value for booking in plan.bookings for value in asdict(booking).values()]
    return texts


def test_name_pools_never_contain_ade() -> None:
    for name in (*FIRST_NAMES, *LAST_NAMES):
        assert "ade" not in name.lower(), name


@pytest.mark.parametrize("rng_seed", range(25))
def test_no_generated_text_contains_ade(rng_seed: int) -> None:
    plan = generate_plan(random.Random(rng_seed), NOW)
    for text in all_text(plan):
        assert "ade" not in text.lower(), text


def test_plan_has_plenty_of_realistic_slots() -> None:
    plan = generate_plan(random.Random(1), NOW)
    assert len(plan.providers) == 8
    assert len(plan.slots) >= 400
    for provider in plan.providers:
        first_name, last_name = provider.removeprefix("Dr ").split(" ")
        assert first_name in FIRST_NAMES
        assert last_name in LAST_NAMES
    assert len({slot.id for slot in plan.slots}) == len(plan.slots)
    for slot in plan.slots:
        start, end = parse_iso(slot.start), parse_iso(slot.end)
        assert start > NOW
        assert (end - start).total_seconds() == 30 * 60
    # Nobody is double-booked into two slots at the same moment of their own diary.
    per_doctor_start = Counter((slot.provider, slot.start) for slot in plan.slots)
    assert max(per_doctor_start.values()) == 1


def test_plan_bookings_are_valid() -> None:
    plan = generate_plan(random.Random(2), NOW)
    slot_ids = {slot.id for slot in plan.slots}
    assert plan.bookings
    assert len({b.slot_id for b in plan.bookings}) == len(plan.bookings)
    for booking in plan.bookings:
        assert booking.slot_id in slot_ids
        assert " " in booking.name
        assert booking.email == booking.email.lower()
        assert booking.email.endswith("@example.com")
    stamps = [b.created_at for b in plan.bookings]
    assert stamps == sorted(stamps)
    assert all(parse_iso(stamp) < NOW for stamp in stamps)


def test_same_seed_same_plan_different_seed_different_plan() -> None:
    first = generate_plan(random.Random(7), NOW)
    again = generate_plan(random.Random(7), NOW)
    other = generate_plan(random.Random(8), NOW)
    assert first == again
    assert first.providers != other.providers


def test_seed_database_writes_and_replaces(conn: sqlite3.Connection) -> None:
    first = seed_database(conn, rng_seed=1)
    count = conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
    booked = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    assert (count, booked) == (first.slots, first.bookings)
    seed_database(conn, rng_seed=2)
    assert conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0] != 0
    confirmed = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    assert confirmed == total  # the old bookings are gone, not stacked up


def test_seed_if_empty_only_seeds_once(conn: sqlite3.Connection) -> None:
    assert seed_if_empty(conn, rng_seed=3) is not None
    before = conn.execute("SELECT group_concat(id) FROM slots").fetchone()[0]
    assert seed_if_empty(conn, rng_seed=4) is None
    assert conn.execute("SELECT group_concat(id) FROM slots").fetchone()[0] == before


def test_seed_endpoint_replaces_data_and_marks_booked_slots(client: TestClient) -> None:
    response = client.post("/seed")
    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) >= 400
    assert any(not slot["available"] for slot in slots)
    assert any(slot["available"] for slot in slots)
    assert all(slot["provider"].startswith("Dr ") for slot in slots)
    # A seeded patient's bookings are listed, oldest first.
    booked = next(slot for slot in slots if not slot["available"])
    assert booked["id"].startswith("slot-")


def test_seed_endpoint_needs_the_api_key(client: TestClient) -> None:
    assert TestClient(client.app).post("/seed").status_code == 401
    assert (
        TestClient(client.app).post("/seed", headers={"X-API-Key": API_KEY}).status_code
        == 200
    )
