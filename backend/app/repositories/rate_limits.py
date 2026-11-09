import sqlite3


class RateLimitRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def hits_since(self, bucket: str, since: float) -> list[float]:
        """Hit timestamps for this bucket newer than `since`, oldest first."""
        rows = self._conn.execute(
            "SELECT hit_at FROM rate_limit_hits "
            "WHERE bucket = ? AND hit_at > ? ORDER BY hit_at",
            (bucket, since),
        )
        return [float(row["hit_at"]) for row in rows]

    def record(self, bucket: str, at: float) -> None:
        self._conn.execute(
            "INSERT INTO rate_limit_hits (bucket, hit_at) VALUES (?, ?)", (bucket, at)
        )

    def prune(self, before: float) -> None:
        self._conn.execute("DELETE FROM rate_limit_hits WHERE hit_at <= ?", (before,))

    def clear(self) -> None:
        self._conn.execute("DELETE FROM rate_limit_hits")
