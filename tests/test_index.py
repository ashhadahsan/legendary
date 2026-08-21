from datetime import datetime, timezone
from pathlib import Path

from legendary.index import rebuild, search
from legendary.models import Anchor, Memory
from legendary.store import save


def mem(
    i: str, title: str, body: str, file: str | None = None, status: str = "active"
) -> Memory:
    return Memory(
        id=i,
        type="decision",
        title=title,
        body=body,
        status=status,
        created=datetime(2026, 8, 14, tzinfo=timezone.utc),
        anchors=[Anchor(file=file)] if file else [],
    )


def seed(repo: Path):
    save(
        repo,
        mem(
            "mem-1",
            "sqlite retry deadlock",
            "WAL mode deadlocks on retry",
            "src/sync/worker.py",
        ),
    )
    save(repo, mem("mem-2", "auth token refresh", "refresh tokens rotate hourly"))
    save(
        repo,
        mem(
            "mem-3", "old sqlite note", "deprecated sqlite advice", status="deprecated"
        ),
    )
    rebuild(repo)


def test_search_finds_relevant_memory(repo: Path):
    seed(repo)
    hits = search(repo, "sqlite deadlock")
    assert hits and hits[0][0] == "mem-1"
    assert hits[0][1] > 0  # positive relevance score


def test_search_excludes_deprecated(repo: Path):
    seed(repo)
    ids = [h[0] for h in search(repo, "sqlite")]
    assert "mem-3" not in ids


def test_search_handles_special_characters(repo: Path):
    seed(repo)
    # must not raise an FTS5 syntax error
    assert search(repo, 'weird "query" AND (stuff) -x') is not None


def test_search_empty_query_returns_empty(repo: Path):
    seed(repo)
    assert search(repo, "   ") == []


def test_anchor_files_queryable(repo: Path):
    seed(repo)
    from legendary.index import files_for

    assert files_for(repo, "mem-1") == ["src/sync/worker.py"]
    assert files_for(repo, "mem-2") == []


def test_rebuild_is_idempotent(repo: Path):
    seed(repo)
    first = search(repo, "sqlite")
    rebuild(repo)
    assert search(repo, "sqlite") == first


def test_search_auto_rebuilds_when_index_missing(repo: Path):
    # the clone case: memories committed, index.db gitignored and absent
    seed(repo)
    from legendary.index import db_path

    db_path(repo).unlink()
    assert [h[0] for h in search(repo, "sqlite deadlock")] == ["mem-1"]


def test_search_recovers_from_corrupt_index(repo: Path):
    seed(repo)
    from legendary.index import db_path

    db_path(repo).write_bytes(b"this is definitely not a sqlite database")
    assert [h[0] for h in search(repo, "sqlite deadlock")] == ["mem-1"]


def test_triggers_indexed_for_active_memories(repo: Path):
    from legendary.index import all_triggers

    save(
        repo,
        mem("mem-t", "locked episode", "body").model_copy(
            update={"type": "episode", "triggers": ["database is locked"]}
        ),
    )
    save(repo, mem("mem-d", "dead note", "body", status="deprecated"))
    rebuild(repo)
    assert all_triggers(repo) == [("mem-t", "database is locked")]
