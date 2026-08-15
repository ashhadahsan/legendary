"""Regression tests for issues found in code review of the v1 branch."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from legendary import service
from legendary.anchor import resolve_and_hash
from legendary.index import db_path, rebuild, search
from legendary.models import Anchor, Memory
from legendary.rank import recall
from legendary.store import _path, load, save


def test_naive_created_does_not_break_recall(repo: Path):
    """A hand-edited naive timestamp must not crash recall for the whole repo."""
    m = Memory(
        id="mem-naive",
        type="decision",
        title="hand edited memory",
        body="someone typed the date by hand",
        created=datetime(2026, 8, 1),  # naive on purpose
    )
    assert m.created.tzinfo is not None  # coerced to UTC at validation
    save(repo, m)
    rebuild(repo)
    results = recall(
        repo, "hand edited", now=datetime(2026, 8, 14, tzinfo=timezone.utc)
    )
    assert results[0]["id"] == "mem-naive"


def test_naive_created_survives_markdown_round_trip(repo: Path):
    raw = (
        "---\n"
        "id: mem-raw\n"
        "type: decision\n"
        "title: raw file\n"
        "created: 2026-08-01 12:00:00\n"
        "source: agent\n"
        "status: active\n"
        "---\n"
        "body text\n"
    )
    (repo / ".legendary" / "memories").mkdir(parents=True, exist_ok=True)
    (repo / ".legendary" / "memories" / "mem-raw.md").write_text(raw, encoding="utf-8")
    assert load(repo, "mem-raw").created.tzinfo is not None


def test_non_dict_anchor_raises_value_error_not_type_error(repo: Path):
    """LLMs emit ["src/foo.py"] instead of [{"file": ...}]; must be catchable."""
    with pytest.raises(ValueError, match="must be an object"):
        service.remember(
            repo_root=repo,
            type="episode",
            title="x",
            body="y",
            anchors=["src/sync/worker.py"],  # type: ignore[list-item]
        )


def test_locked_index_is_not_deleted(repo: Path, monkeypatch):
    """Lock contention is transient - it must never destroy a healthy index."""
    service.remember(
        repo_root=repo, type="decision", title="keep me", body="important", anchors=[]
    )
    assert db_path(repo).exists()
    size_before = db_path(repo).stat().st_size

    import legendary.index as index_mod

    class LockedConn:
        """sqlite3.Connection is immutable, so stand in for it entirely."""

        def executescript(self, script):
            raise sqlite3.OperationalError("database is locked")

        def close(self):
            pass

    monkeypatch.setattr(index_mod.sqlite3, "connect", lambda *a, **k: LockedConn())
    with pytest.raises(sqlite3.OperationalError):
        index_mod._connect(repo)
    monkeypatch.undo()

    assert db_path(repo).exists()
    assert db_path(repo).stat().st_size == size_before


def test_symbol_anchor_allowed_in_unsupported_language(repo: Path):
    """Go/Rust/Java repos must still be able to anchor by symbol name."""
    (repo / "main.go").write_text("func Serve() {\n\treturn\n}\n", encoding="utf-8")
    anchor = resolve_and_hash(repo, Anchor(file="main.go", symbol="Serve"))
    assert anchor.content_hash is not None
    assert anchor.symbol == "Serve"


def test_unresolvable_symbol_still_rejected_in_supported_language(repo: Path):
    with pytest.raises(ValueError, match="line range"):
        resolve_and_hash(repo, Anchor(file="src/sync/worker.py", symbol="NoSuchThing"))


def test_missing_transcript_reports_the_real_problem(repo: Path):
    from legendary.extract import extract_from_transcript

    with pytest.raises(RuntimeError, match="transcript not found"):
        extract_from_transcript(repo, repo / "does_not_exist.jsonl")


@pytest.mark.parametrize("bad_id", ["../../etc/passwd", "..", "a/b", "x\\y", ""])
def test_memory_id_traversal_rejected(repo: Path, bad_id: str):
    with pytest.raises(ValueError, match="invalid memory id"):
        _path(repo, bad_id)


def test_deprecate_rejects_traversal_id(repo: Path):
    with pytest.raises(ValueError):
        service.deprecate(repo, "../../../etc/passwd", reason="pwn")


def test_recall_k_above_default_limit_is_honoured(repo: Path):
    for n in range(60):
        save(
            repo,
            Memory(
                id=f"mem-{n:03d}",
                type="reference",
                title=f"widget note {n}",
                body="the same widget body text",
                created=datetime(2026, 8, 1, tzinfo=timezone.utc),
            ),
        )
    rebuild(repo)
    # search() still defaults to 50; the fix was rank asking for a wider pool
    assert len(search(repo, "widget body", limit=100)) >= 60
    assert len(recall(repo, "widget body", k=55)) == 55


def test_unicode_round_trips_through_the_store(repo: Path):
    m = Memory(
        id="mem-uni",
        type="convention",
        title="naïve café — déjà vu ✓",
        body="日本語のメモ, emoji 🎯, and «guillemets»",
        created=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    save(repo, m)
    loaded = load(repo, "mem-uni")
    assert loaded.title == m.title
    assert loaded.body.strip() == m.body


def test_upsert_matches_full_rebuild(repo: Path):
    """Incremental indexing must produce the same result as a full rebuild."""
    for n in range(5):
        service.remember(
            repo_root=repo,
            type="decision",
            title=f"alpha note {n}",
            body="shared alpha body",
            anchors=[{"file": "src/sync/worker.py"}],
        )
    incremental = search(repo, "alpha body", limit=100)
    rebuild(repo)
    assert search(repo, "alpha body", limit=100) == incremental


def test_remember_does_not_rebuild_whole_index(repo: Path, monkeypatch):
    """Writes must be O(1): a full rebuild per write made bulk writes O(n^2)."""
    import legendary.index as index_mod

    service.remember(
        repo_root=repo, type="decision", title="seed", body="s", anchors=[]
    )

    calls = {"n": 0}
    real_rebuild = index_mod.rebuild

    def counting_rebuild(root):
        calls["n"] += 1
        return real_rebuild(root)

    monkeypatch.setattr(index_mod, "rebuild", counting_rebuild)
    for n in range(5):
        service.remember(
            repo_root=repo, type="decision", title=f"n{n}", body="b", anchors=[]
        )
    assert calls["n"] == 0


def test_upsert_populates_index_on_fresh_clone(repo: Path):
    """A clone has memories but no index; one upsert must not leave it partial."""
    for n in range(4):
        service.remember(
            repo_root=repo,
            type="reference",
            title=f"clone note {n}",
            body="cloned body",
        )
    db_path(repo).unlink()  # simulate the gitignored index being absent
    service.remember(
        repo_root=repo, type="reference", title="clone note new", body="cloned body"
    )
    assert len(search(repo, "cloned body", limit=100)) == 5


def test_deprecate_leaves_search_via_upsert(repo: Path):
    mid = service.remember(
        repo_root=repo, type="decision", title="temporary rule", body="rule body"
    )["id"]
    assert search(repo, "rule body")
    service.deprecate(repo, mid, reason="obsolete")
    assert all(h[0] != mid for h in search(repo, "rule body"))


def test_supersede_updates_both_memories_in_index(repo: Path):
    old_id = service.remember(
        repo_root=repo, type="decision", title="old rule", body="beta body"
    )["id"]
    new_id = service.remember(
        repo_root=repo,
        type="decision",
        title="new rule",
        body="beta body",
        supersedes=old_id,
    )["id"]
    ids = [h[0] for h in search(repo, "beta body", limit=100)]
    assert new_id in ids and old_id not in ids
