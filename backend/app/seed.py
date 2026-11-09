"""
Random demo data: doctors, plenty of slots, and some existing bookings.

Run on startup when the database is empty (SEED_ON_STARTUP), from the
dashboard (POST /seed), or by hand:

    uv run python -m app.seed             # only if there are no slots yet
    uv run python -m app.seed --force     # replace everything
    uv run python -m app.seed --seed 42   # reproducible output
"""

import argparse
import logging
import random
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from app.config import settings
from app.database import connect, init_db, transaction
from app.logging_config import configure_logging
from app.models import Slot
from app.repositories.bookings import BookingRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.rate_limits import RateLimitRepository
from app.repositories.slots import SlotRepository

logger = logging.getLogger(__name__)

FIRST_NAMES = (
    "Chioma",
    "Tunde",
    "Ngozi",
    "Emeka",
    "Kemi",
    "Ifeanyi",
    "Zainab",
    "Musa",
    "Halima",
    "Segun",
    "Bisi",
    "Yetunde",
    "Obinna",
    "Amara",
    "Folake",
    "Tobi",
    "Nneka",
    "Ibrahim",
    "Aisha",
    "Chidi",
    "Uche",
    "Hauwa",
    "Babatunde",
    "Kelechi",
    "Funke",
    "Damilola",
    "Ireti",
    "Seyi",
    "Rasheed",
    "Blessing",
)

LAST_NAMES = (
    "Okafor",
    "Balogun",
    "Nwosu",
    "Okonkwo",
    "Bello",
    "Eze",
    "Ogunleye",
    "Lawal",
    "Abubakar",
    "Obi",
    "Okeke",
    "Salami",
    "Umeh",
    "Yusuf",
    "Onyeka",
    "Akinola",
    "Nwankwo",
    "Ibrahim",
    "Mohammed",
    "Oyelaran",
    "Chukwu",
    "Ogundipe",
    "Danjuma",
    "Egwu",
    "Olawale",
    "Ekwueme",
    "Garba",
    "Idowu",
    "Anyanwu",
    "Suleiman",
)

PROVIDER_COUNT = 8
WORKING_DAYS = 7
SLOT_MINUTES = 30
BOOKED_SHARE = 0.25
PATIENT_POOL = 45

# The clinic keeps Lagos hours (UTC+1, no daylight saving); times are stored in UTC.
CLINIC_TZ = timezone(timedelta(hours=1))
# Local start times: 09:00 to 16:30 with an hour off at 13:00.
DAY_STARTS = tuple(
    (hour, minute) for hour in range(9, 17) for minute in (0, 30) if hour != 13
)


@dataclass(frozen=True, slots=True)
class SeedBooking:
    slot_id: str
    name: str
    email: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SeedPlan:
    providers: list[str]
    slots: list[Slot]
    bookings: list[SeedBooking]


@dataclass(frozen=True, slots=True)
class SeedSummary:
    providers: int
    slots: int
    bookings: int


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_ms(moment: datetime) -> str:
    return (
        moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _doctors(rng: random.Random, count: int) -> list[tuple[str, str]]:
    """`count` (first, last) pairs where no first or last name repeats."""
    firsts = rng.sample(FIRST_NAMES, count)
    lasts = rng.sample(LAST_NAMES, count)
    return list(zip(firsts, lasts, strict=True))


def _patients(
    rng: random.Random, count: int, exclude: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """`count` distinct full names, none of them a doctor's."""
    pool = [
        (first, last)
        for first in FIRST_NAMES
        for last in LAST_NAMES
        if (first, last) not in exclude
    ]
    return rng.sample(pool, count)


def _working_days(now: datetime, count: int) -> list[datetime]:
    days: list[datetime] = []
    day = now.astimezone(CLINIC_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    while len(days) < count:
        day += timedelta(days=1)  # always start tomorrow so every slot is in the future
        if day.weekday() < 5:
            days.append(day)
    return days


def generate_plan(rng: random.Random, now: datetime) -> SeedPlan:
    doctors = _doctors(rng, PROVIDER_COUNT)
    providers = [f"Dr {first} {last}" for first, last in doctors]

    slots: list[Slot] = []
    for day in _working_days(now, WORKING_DAYS):
        for index, provider in enumerate(providers, start=1):
            if rng.random() < 0.12:  # this doctor is off today
                continue
            starts = sorted(rng.sample(DAY_STARTS, rng.randint(9, len(DAY_STARTS))))
            for hour, minute in starts:
                start = day.replace(hour=hour, minute=minute)
                end = start + timedelta(minutes=SLOT_MINUTES)
                slots.append(
                    Slot(
                        id=f"slot-{index}-{start:%Y%m%d}-{start:%H%M}",
                        provider=provider,
                        start=_iso(start),
                        end=_iso(end),
                    )
                )

    patients = _patients(rng, PATIENT_POOL, exclude=doctors)
    booked = rng.sample(slots, int(len(slots) * BOOKED_SHARE))
    stamps = sorted(
        now - timedelta(minutes=rng.randint(5, 4 * 24 * 60)) for _ in booked
    )
    bookings: list[SeedBooking] = []
    for slot, stamp in zip(booked, stamps, strict=True):
        first, last = rng.choice(patients)
        bookings.append(
            SeedBooking(
                slot_id=slot.id,
                name=f"{first} {last}",
                email=f"{first}.{last}@example.com".lower(),
                created_at=_iso_ms(stamp),
            )
        )
    return SeedPlan(providers=providers, slots=slots, bookings=bookings)


def _apply(conn: sqlite3.Connection, plan: SeedPlan) -> SeedSummary:
    SlotRepository(conn).clear()
    BookingRepository(conn).clear()
    IdempotencyRepository(conn).clear()
    RateLimitRepository(conn).clear()
    SlotRepository(conn).insert_many(plan.slots)
    bookings = BookingRepository(conn)
    for booking in plan.bookings:
        bookings.create(
            slot_id=booking.slot_id,
            name=booking.name,
            email=booking.email,
            created_at=booking.created_at,
        )
    return SeedSummary(len(plan.providers), len(plan.slots), len(plan.bookings))


def seed_database(
    conn: sqlite3.Connection,
    *,
    rng_seed: int | None = None,
    now: datetime | None = None,
) -> SeedSummary:
    """Replace everything (slots, bookings, idempotency keys, rate limits)."""
    plan = generate_plan(random.Random(rng_seed), now or datetime.now(UTC))
    with transaction(conn):
        summary = _apply(conn, plan)
    logger.info(
        "Seeded %d providers, %d slots, %d bookings",
        summary.providers,
        summary.slots,
        summary.bookings,
    )
    return summary


def seed_if_empty(
    conn: sqlite3.Connection, *, rng_seed: int | None = None
) -> SeedSummary | None:
    """Seed only when there are no slots. Safe with several workers starting at
    once: the check happens inside the write transaction."""
    plan = generate_plan(random.Random(rng_seed), datetime.now(UTC))
    with transaction(conn):
        if SlotRepository(conn).count() > 0:
            return None
        summary = _apply(conn, plan)
    logger.info(
        "Empty database seeded: %d providers, %d slots, %d bookings",
        summary.providers,
        summary.slots,
        summary.bookings,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill the database with random demo data."
    )
    parser.add_argument("--force", action="store_true", help="replace existing data")
    parser.add_argument("--seed", type=int, default=None, help="reproducible output")
    args = parser.parse_args()

    configure_logging(settings.log_level)
    init_db(settings.database_path)
    conn = connect(settings.database_path)
    try:
        if args.force:
            summary = seed_database(conn, rng_seed=args.seed)
        else:
            summary = seed_if_empty(conn, rng_seed=args.seed)
    finally:
        conn.close()
    if summary is None:
        print("Slots already exist; nothing seeded. Use --force to replace them.")
    else:
        print(
            f"Seeded {summary.providers} doctors, {summary.slots} slots, "
            f"{summary.bookings} bookings."
        )


if __name__ == "__main__":
    main()
