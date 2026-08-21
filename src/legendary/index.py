"""Derived SQLite FTS5 index at <repo>/.legendary/index.db. Always rebuildable."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from legendary.models import Memory
from legendary.store import legendary_dir, load_all, memories_dir

# Bump when _SCHEMA changes: a stale index is dropped and rebuilt from markdown.
_SCHEMA_VERSION = 3

_SCHEMA = """
-- porter stemming: an agent searching "deadlock" must find a memory that says
-- "deadlocked", and "transactions" must find "transaction". Without it FTS5
-- matches exact terms only and silently loses memories to word-form drift.
CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(
    id UNINDEXED, title, body, tags,
    tokenize = 'porter unicode61'
);
CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER);
CREATE TABLE IF NOT EXISTS mem_meta (
    id TEXT PRIMARY KEY, type TEXT, status TEXT, created TEXT
);
CREATE TABLE IF NOT EXISTS mem_anchors (
    memory_id TEXT, file TEXT
);
CREATE TABLE IF NOT EXISTS mem_triggers (
    memory_id TEXT, trigger TEXT
);
"""


def db_path(repo_root: Path) -> Path:
    return legendary_dir(repo_root) / "index.db"


def _connect(repo_root: Path) -> sqlite3.Connection:
    legendary_dir(repo_root).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path(repo_root))
    try:
        conn.executescript(_SCHEMA)
    except sqlite3.OperationalError:
        # "database is locked" is transient contention, NOT corruption.
        # Deleting here would destroy a healthy index under an active writer.
        conn.close()
        raise
    except sqlite3.DatabaseError:
        # Corrupt index: the markdown store is canonical, so throw it away and
        # start clean. Deleting before reconnecting keeps rebuild() from
        # recursing (rebuild calls _connect).
        conn.close()
        db_path(repo_root).unlink(missing_ok=True)
        conn = sqlite3.connect(db_path(repo_root))
        conn.executescript(_SCHEMA)
    return _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Drop and recreate the index when the schema version has moved on.

    Safe because the markdown store is canonical: the emptied index is
    repopulated by _ensure_populated on the next read.
    """
    row = conn.execute("SELECT version FROM schema_meta").fetchone()
    if row and row[0] == _SCHEMA_VERSION:
        return conn
    with conn:
        conn.execute("DROP TABLE IF EXISTS mem_fts")
        conn.execute("DROP TABLE IF EXISTS mem_meta")
        conn.execute("DROP TABLE IF EXISTS mem_anchors")
        conn.execute("DROP TABLE IF EXISTS mem_triggers")
        conn.executescript(_SCHEMA)
        conn.execute("DELETE FROM schema_meta")
        conn.execute("INSERT INTO schema_meta VALUES (?)", (_SCHEMA_VERSION,))
    return conn


def _ensure_populated(repo_root: Path, conn: sqlite3.Connection) -> sqlite3.Connection:
    """Auto-rebuild when the index is empty but memories exist on disk.

    Covers the git-native case: a teammate clones the repo (memories committed,
    index.db gitignored) and calls recall before ever running `init`.
    """
    count = conn.execute("SELECT COUNT(*) FROM mem_meta").fetchone()[0]
    if count:
        return conn
    if not any(memories_dir(repo_root).glob("*.md")):
        return conn
    conn.close()
    rebuild(repo_root)
    return _connect(repo_root)


def _delete_rows(conn: sqlite3.Connection, memory_id: str) -> None:
    conn.execute("DELETE FROM mem_fts WHERE id = ?", (memory_id,))
    conn.execute("DELETE FROM mem_meta WHERE id = ?", (memory_id,))
    conn.execute("DELETE FROM mem_anchors WHERE memory_id = ?", (memory_id,))
    conn.execute("DELETE FROM mem_triggers WHERE memory_id = ?", (memory_id,))


def _insert_rows(conn: sqlite3.Connection, m: Memory) -> None:
    conn.execute(
        "INSERT INTO mem_fts (id, title, body, tags) VALUES (?,?,?,?)",
        (m.id, m.title, m.body, " ".join(m.tags)),
    )
    conn.execute(
        "INSERT INTO mem_meta VALUES (?,?,?,?)",
        (m.id, m.type, m.status, m.created.isoformat()),
    )
    for a in m.anchors:
        conn.execute("INSERT INTO mem_anchors VALUES (?,?)", (m.id, a.file))
    for trig in m.triggers:
        conn.execute("INSERT INTO mem_triggers VALUES (?,?)", (m.id, trig))


def upsert(repo_root: Path, memory: Memory) -> None:
    """Index a single memory in place.

    Writes are O(1) instead of O(n): rebuilding the whole index on every
    `remember` made bulk writes quadratic (measured at ~31ms/write with only
    70 memories, growing linearly with store size).
    """
    # _ensure_populated first: on a fresh clone the index is empty while the
    # store is full, and inserting one row would leave it permanently partial
    # (a non-empty index never triggers the auto-rebuild).
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        with conn:
            _delete_rows(conn, memory.id)
            _insert_rows(conn, memory)
    finally:
        conn.close()


def remove(repo_root: Path, memory_id: str) -> None:
    """Drop a single memory from the index."""
    conn = _connect(repo_root)
    try:
        with conn:
            _delete_rows(conn, memory_id)
    finally:
        conn.close()


def rebuild(repo_root: Path) -> int:
    """Rebuild the whole index from the markdown store. Returns count indexed."""
    conn = _connect(repo_root)
    with conn:
        conn.execute("DELETE FROM mem_fts")
        conn.execute("DELETE FROM mem_meta")
        conn.execute("DELETE FROM mem_anchors")
        conn.execute("DELETE FROM mem_triggers")
        memories = load_all(repo_root)
        for m in memories:
            _insert_rows(conn, m)
    conn.close()
    return len(memories)


def _fts_query(query: str) -> str:
    """Sanitize free text into a lenient OR-of-quoted-terms FTS5 query."""
    terms = [t.replace('"', "") for t in query.split()]
    terms = [t for t in terms if t]
    return " OR ".join(f'"{t}"' for t in terms)


def search(repo_root: Path, query: str, limit: int = 50) -> list[tuple[str, float]]:
    """Return [(memory_id, relevance)] for active memories, best first."""
    q = _fts_query(query)
    if not q:
        return []
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        rows = conn.execute(
            """
            SELECT f.id, -bm25(mem_fts) AS rel
            FROM mem_fts f JOIN mem_meta m ON m.id = f.id
            WHERE mem_fts MATCH ? AND m.status = 'active'
            -- tie-break on id: without it, equally-relevant memories come back
            -- in physical row order, so an incrementally-built index and a
            -- freshly-rebuilt one rank the same repo differently.
            ORDER BY rel DESC, f.id LIMIT ?
            """,
            (q, limit),
        ).fetchall()
        return [(r[0], float(r[1])) for r in rows]
    finally:
        conn.close()


def files_for(repo_root: Path, memory_id: str) -> list[str]:
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        rows = conn.execute(
            "SELECT file FROM mem_anchors WHERE memory_id = ?", (memory_id,)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def memories_for_file(repo_root: Path, file: str) -> list[str]:
    """Active memory ids anchored to a file (repo-relative path)."""
    # _ensure_populated, not bare _connect: the PreToolUse hook must work on a
    # fresh clone where memories are committed but index.db is absent.
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT a.memory_id FROM mem_anchors a
            JOIN mem_meta m ON m.id = a.memory_id
            WHERE a.file = ? AND m.status = 'active'
            ORDER BY a.memory_id
            """,
            (file,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def all_triggers(repo_root: Path) -> list[tuple[str, str]]:
    """(memory_id, trigger) pairs for active memories, for guard matching."""
    conn = _ensure_populated(repo_root, _connect(repo_root))
    try:
        rows = conn.execute(
            """
            SELECT t.memory_id, t.trigger FROM mem_triggers t
            JOIN mem_meta m ON m.id = t.memory_id
            WHERE m.status = 'active'
            ORDER BY t.memory_id, t.trigger
            """
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()
