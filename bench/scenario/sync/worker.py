"""Writes rows to the shared store. Used by many threads at once."""

from sync.db import connect


def write_rows(db_path: str, worker: str, count: int) -> int:
    """Write `count` rows. Returns the number written."""
    conn = connect(db_path)
    written = 0
    try:
        for n in range(count):
            conn.execute("INSERT INTO rows VALUES (?, ?)", (worker, n))
            conn.commit()
            written += 1
    finally:
        conn.close()
    return written
