"""Concurrency tests. Both fail until the writers take the write lock correctly."""

from concurrent.futures import ThreadPoolExecutor

from sync.db import connect, ensure_schema
from sync.reporter import record_hit
from sync.worker import bump_counter

THREADS = 6
BUMPS = 15


def run_concurrently(fn, db_path):
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = [pool.submit(fn, db_path, f"w{i}", BUMPS) for i in range(THREADS)]
        return [f.result() for f in futures]


def total(db_path):
    conn = connect(db_path)
    try:
        return conn.execute("SELECT value FROM counter WHERE name='total'").fetchone()[
            0
        ]
    finally:
        conn.close()


def test_worker_counter_is_exact_under_concurrency(tmp_path):
    db = str(tmp_path / "sync.db")
    ensure_schema(db)
    run_concurrently(bump_counter, db)
    assert total(db) == THREADS * BUMPS


def test_reporter_counter_is_exact_under_concurrency(tmp_path):
    db = str(tmp_path / "sync.db")
    ensure_schema(db)
    run_concurrently(record_hit, db)
    assert total(db) == THREADS * BUMPS
