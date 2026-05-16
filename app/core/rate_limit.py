from collections import deque
from datetime import datetime, timedelta, timezone


class InMemorySlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[datetime]] = {}

    def allow(self, key: str) -> bool:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)
        queue = self._events.setdefault(key, deque())

        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= self.max_requests:
            return False

        queue.append(now)
        return True


create_url_rate_limiter = InMemorySlidingWindowRateLimiter(
    max_requests=30,
    window_seconds=60 * 60,
)
