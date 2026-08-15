"""Shared SQLite helpers for the sync package."""

import sqlite3

# Generous busy timeout is already configured - lock waits are not the issue.
BUSY_TIMEOUT_MS = 5000


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.isolation_level = None  # we manage transactions explicitly
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def ensure_schema(path: str) -> None:
    conn = connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS counter (name TEXT PRIMARY KEY, value INTEGER)"
    )
    conn.execute("INSERT OR IGNORE INTO counter VALUES ('total', 0)")
    conn.close()
