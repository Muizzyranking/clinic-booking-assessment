from datetime import UTC, datetime


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; naive values are treated as UTC."""
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
