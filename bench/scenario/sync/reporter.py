"""Aggregates rows written by workers. Same concurrency profile as worker.py."""

from sync.db import connect


def record_summary(db_path: str, worker: str, count: int) -> int:
    """Write `count` summary rows. Returns the number written."""
    conn = connect(db_path)
    written = 0
    try:
        for n in range(count):
            conn.execute("INSERT INTO rows VALUES (?, ?)", (f"summary-{worker}", n))
            conn.commit()
            written += 1
    finally:
        conn.close()
    return written
