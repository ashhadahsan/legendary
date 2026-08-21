import time

from cache.refresh import refresh_cache

KEYS = [f"k{i}" for i in range(40)]
DEADLINE_S = 0.30


def test_refresh_cache_completes_before_deadline():
    started = time.monotonic()
    result = refresh_cache(KEYS)
    elapsed = time.monotonic() - started
    assert set(result) == set(KEYS)
    assert elapsed < DEADLINE_S, f"took {elapsed:.2f}s, deadline is {DEADLINE_S}s"
