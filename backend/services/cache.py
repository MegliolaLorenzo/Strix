from __future__ import annotations

import hashlib
from collections import OrderedDict


class CheckCache:
    """Simple in-memory LRU cache for fact-check results."""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    def _key(self, text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, text: str) -> dict | None:
        key = self._key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, text: str, result: dict):
        key = self._key(text)
        self._cache[key] = result
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


cache = CheckCache()
