from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def limit(self, key_prefix: str, max_calls: int, window_seconds: int) -> Callable:
        def dependency(request: Request) -> None:
            client_key = request.client.host if request.client else "anonymous"
            key = f"{key_prefix}:{client_key}"
            now = time.time()
            with self._lock:
                calls = self._buckets[key]
                # purge old entries
                while calls and now - calls[0] > window_seconds:
                    calls.pop(0)
                if len(calls) >= max_calls:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later.",
                    )
                calls.append(now)

        return dependency


rate_limiter = RateLimiter()

