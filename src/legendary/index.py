"""Derived SQLite FTS5 index at <repo>/.legendary/index.db. Always rebuildable."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from legendary.store import legendary_dir, load_all, memories_dir

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(
    id UNINDEXED, title, body, tags
);
CREATE TABLE IF NOT EXISTS mem_meta (
    id TEXT PRIMARY KEY, type TEXT, status TEXT, created TEXT
);
CREATE TABLE IF NOT EXISTS mem_anchors (
    memory_id TEXT, file TEXT
);
"""


def db_path(repo_root: Path) -> Path:
    return legendary_dir(repo_root) / "index.db"


def _connect(repo_root: Path) -> sqlite3.Connection:
    legendary_dir(repo_root).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path(repo_root))
    try:
        conn.executescript(_SCHEMA)
    except sqlite3.DatabaseError:
        # Corrupt index: the markdown store is canonical, so throw it away and
        # start clean. Deleting before reconnecting keeps rebuild() from
        # recursing (rebuild calls _connect).
        conn.close()
        db_path(repo_root).unlink(missing_ok=True)
        conn = sqlite3.connect(db_path(repo_root))
        conn.executescript(_SCHEMA)
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


def rebuild(repo_root: Path) -> int:
    """Rebuild the whole index from the markdown store. Returns count indexed."""
    conn = _connect(repo_root)
    with conn:
        conn.execute("DELETE FROM mem_fts")
        conn.execute("DELETE FROM mem_meta")
        conn.execute("DELETE FROM mem_anchors")
        memories = load_all(repo_root)
        for m in memories:
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
            ORDER BY rel DESC LIMIT ?
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
