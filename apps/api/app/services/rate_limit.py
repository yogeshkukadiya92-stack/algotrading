from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class RateLimitBucket:
    requests: deque[datetime] = field(default_factory=deque)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitBucket] = {}

    def allow(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        bucket = self._buckets.setdefault(key, RateLimitBucket())
        while bucket.requests and bucket.requests[0] < window_start:
            bucket.requests.popleft()
        if len(bucket.requests) >= limit:
            retry_after = max(1, window_seconds - int((now - bucket.requests[0]).total_seconds()))
            return False, retry_after
        bucket.requests.append(now)
        return True, 0

    def reset(self) -> None:
        self._buckets.clear()


rate_limiter = InMemoryRateLimiter()
