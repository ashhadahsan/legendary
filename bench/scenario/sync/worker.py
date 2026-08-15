"""Increments the shared counter. Runs from many threads at once."""

from sync.db import connect


def bump_counter(db_path: str, worker: str, times: int) -> int:
    """Read-modify-write the shared counter `times` times."""
    conn = connect(db_path)
    done = 0
    try:
        for _ in range(times):
            conn.execute("BEGIN")
            current = conn.execute(
                "SELECT value FROM counter WHERE name = 'total'"
            ).fetchone()[0]
            conn.execute(
                "UPDATE counter SET value = ? WHERE name = 'total'", (current + 1,)
            )
            conn.execute("COMMIT")
            done += 1
    finally:
        conn.close()
    return done
