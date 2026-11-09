import logging
import math
import sqlite3
import time
from functools import wraps

from app.config import settings
from app.database import transaction
from app.exceptions import AppException
from app.repositories.rate_limits import RateLimitRepository

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._hits = RateLimitRepository(conn)

    def hit(
        self,
        bucket: str,
        *,
        limit: int = settings.rate_limit_max_attempts,
        window: int = settings.rate_limit_window_seconds,
    ) -> None:
        """Count one attempt for `bucket`, or raise 429 with Retry-After."""
        with transaction(self._conn):
            now = time.time()
            recent = self._hits.hits_since(bucket, now - window)
            if len(recent) >= limit:
                # The hit that must age out before a new one is allowed.
                blocking = recent[len(recent) - limit]
                retry_after = max(1, math.ceil(blocking + window - now))
                logger.warning(
                    "Rate limit hit for %s (retry in %ss)", bucket, retry_after
                )
                raise AppException(
                    "too many attempts, try again later",
                    429,
                    "rate_limited",
                    headers={"Retry-After": str(retry_after)},
                )
            self._hits.record(bucket, now)
            self._hits.prune(now - window)


def rate_limited(
    key,
    *,
    limit: int = settings.rate_limit_max_attempts,
    window: int = settings.rate_limit_window_seconds,
):
    """Limit a method. `key` receives the same arguments as the method and
    returns the bucket name (or None to skip)."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            bucket = key(self, *args, **kwargs)
            if bucket is not None:
                self.rate_limiter.hit(bucket, limit=limit, window=window)
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
