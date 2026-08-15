"""Shared SQLite helpers for the sync package."""

import sqlite3


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(path: str) -> None:
    conn = connect(path)
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS rows (worker TEXT, n INTEGER)")
    conn.close()
