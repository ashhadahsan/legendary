"""Concurrency tests. Both fail until the writers tolerate a busy database."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from sync.db import ensure_schema
from sync.reporter import record_summary
from sync.worker import write_rows

THREADS = 8
ROWS = 40


def run_concurrently(fn, db_path):
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = [pool.submit(fn, db_path, f"w{i}", ROWS) for i in range(THREADS)]
        return [f.result() for f in futures]


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "sync.db")
    ensure_schema(p)
    return p


def test_worker_writes_all_rows_under_concurrency(db_path):
    try:
        results = run_concurrently(write_rows, db_path)
    except sqlite3.OperationalError as exc:
        pytest.fail(f"worker could not write under concurrency: {exc}")
    assert sum(results) == THREADS * ROWS


def test_reporter_writes_all_rows_under_concurrency(db_path):
    try:
        results = run_concurrently(record_summary, db_path)
    except sqlite3.OperationalError as exc:
        pytest.fail(f"reporter could not write under concurrency: {exc}")
    assert sum(results) == THREADS * ROWS
