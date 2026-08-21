"""Pre-populate the cache before the deadline."""

import time

from cache.limits import MAX_CONCURRENT_WORKERS  # noqa: F401  (enforced by tests)

_STORE: dict[str, str] = {}


def _fetch(key: str) -> str:
    """Simulates a slow upstream read."""
    time.sleep(0.01)
    return f"value-for-{key}"


def warm_cache(keys: list[str]) -> dict[str, str]:
    """Populate the cache for every key. Must respect the platform's
    concurrency limit; see cache/limits.py."""
    _STORE.clear()
    for key in keys:
        _STORE[key] = _fetch(key)
    return dict(_STORE)
