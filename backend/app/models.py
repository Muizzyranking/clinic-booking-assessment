import sqlite3
from dataclasses import dataclass, fields
from enum import Enum, StrEnum
from typing import Self, get_type_hints


@dataclass(frozen=True, slots=True)
class Model:
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        hints = get_type_hints(cls)
        values: dict[str, object] = {}
        for field in fields(cls):
            value = row[field.name]
            hint = hints[field.name]
            if isinstance(hint, type) and issubclass(hint, Enum):
                value = hint(value)
            elif hint is bool:
                value = bool(value)
            values[field.name] = value
        return cls(**values)


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Slot(Model):
    id: str
    provider: str
    start: str
    end: str
    available: bool = True


@dataclass(frozen=True, slots=True)
class Booking(Model):
    seq: int
    id: str
    slot_id: str
    name: str
    email: str
    status: BookingStatus
    created_at: str


@dataclass(frozen=True, slots=True)
class IdempotencyRecord(Model):
    key: str
    request_hash: str
    status_code: int
    response: str
