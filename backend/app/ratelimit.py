"""Sliding-window rate limiter.

In-memory: correct for a single backend process (the default deployment). If the API is ever
run with several workers or instances, move this to a shared store (Postgres or Redis).
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_seconds:
                q.popleft()
            if len(q) >= limit:
                retry = int(q[0] + window_seconds - now) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Trop de requêtes, réessayez plus tard.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)
            if len(self._hits) > 50_000:  # bound memory under key-spraying
                for k in [k for k, v in self._hits.items() if not v][:10_000]:
                    del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


TRUSTED_PROXIES = {"127.0.0.1", "::1"}


def client_ip(request: Request) -> str:
    """Peer address; behind the local Next.js proxy, the address that proxy appended.

    Only the last X-Forwarded-For entry is used: it is written by our own proxy, while
    earlier entries can be forged by the client.
    """
    peer = request.client.host if request.client else "unknown"
    if peer in TRUSTED_PROXIES:
        xff = request.headers.get("x-forwarded-for", "")
        last = xff.split(",")[-1].strip()
        if last:
            return last[:64]
    return peer
