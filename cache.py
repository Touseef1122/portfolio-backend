"""
Simple in-memory cache that maintains a pool of greetings per context bucket.

Strategy:
  - Each bucket holds up to MAX_POOL_SIZE greetings
  - get_random() returns a random one if the pool is "full enough"
  - Otherwise it returns None so caller can generate a new greeting
  - Entries expire after TTL hours

For production scale, replace with Redis. For a portfolio site, in-memory is fine.
"""

import random
import time
import threading
from collections import defaultdict

MAX_POOL_SIZE = 20


class GreetingCache:
    def __init__(self, ttl_hours: int = 24):
        self._pools: dict[str, list[tuple[float, str]]] = defaultdict(list)
        self._ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()

    def add(self, bucket: str, greeting: str) -> None:
        with self._lock:
            self._prune(bucket)
            self._pools[bucket].append((time.time(), greeting))
            if len(self._pools[bucket]) > MAX_POOL_SIZE:
                self._pools[bucket] = self._pools[bucket][-MAX_POOL_SIZE:]

    def get_random(self, bucket: str, min_pool_size: int = 5) -> str | None:
        with self._lock:
            self._prune(bucket)
            pool = self._pools[bucket]
            if len(pool) < min_pool_size:
                return None
            _, greeting = random.choice(pool)
            return greeting

    def size(self) -> int:
        with self._lock:
            return sum(len(p) for p in self._pools.values())

    def clear(self) -> None:
        with self._lock:
            self._pools.clear()

    def _prune(self, bucket: str) -> None:
        cutoff = time.time() - self._ttl_seconds
        self._pools[bucket] = [
            (ts, g) for ts, g in self._pools[bucket] if ts > cutoff
        ]
