"""Enforces the platform's concurrency limit during tests.

Any code that creates more than MAX_CONCURRENT_WORKERS live threads is killed,
the same way the production platform kills it.
"""

import threading

import pytest
from cache.limits import MAX_CONCURRENT_WORKERS


class ConcurrencyLimitExceeded(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def enforce_worker_limit():
    peak = {"n": 0}
    stop = threading.Event()
    ready = threading.Event()

    def watch():
        # baseline is taken from inside the watcher so the watcher itself is
        # not counted as one of the workers under test
        baseline = threading.active_count()
        ready.set()
        while not stop.wait(0.001):
            peak["n"] = max(peak["n"], threading.active_count() - baseline)

    watcher = threading.Thread(daemon=True, target=watch)
    watcher.start()
    ready.wait(timeout=1)
    yield
    stop.set()
    watcher.join(timeout=1)
    if peak["n"] > MAX_CONCURRENT_WORKERS:
        raise ConcurrencyLimitExceeded(
            f"platform limit exceeded: peaked at {peak['n']} concurrent workers, "
            f"limit is {MAX_CONCURRENT_WORKERS}"
        )
