from datetime import datetime, timezone
from pathlib import Path

from legendary.anchor import resolve_and_hash
from legendary.index import rebuild
from legendary.models import Anchor, Memory
from legendary.rank import recall
from legendary.store import save


def mk(
    repo: Path,
    i: str,
    title: str,
    body: str,
    *,
    file: str | None = None,
) -> Memory:
    anchors = []
    if file:
        anchors = [resolve_and_hash(repo, Anchor(file=file))]
    m = Memory(
        id=i,
        type="decision",
        title=title,
        body=body,
        created=datetime(2026, 8, 14, tzinfo=timezone.utc),
        anchors=anchors,
    )
    save(repo, m)
    return m


def test_recall_returns_ranked_results_with_verdicts(repo: Path):
    mk(
        repo,
        "mem-1",
        "sqlite deadlock fix",
        "busy_timeout fixes WAL deadlock",
        file="src/sync/worker.py",
    )
    mk(repo, "mem-2", "css grid notes", "grid beats flexbox here")
    rebuild(repo)
    results = recall(repo, "sqlite deadlock")
    assert results[0]["id"] == "mem-1"
    assert results[0]["staleness"] == "fresh"
    assert "title" in results[0] and "body" in results[0]


def test_files_in_focus_boosts_anchored_memory(repo: Path):
    mk(repo, "mem-1", "sync worker note", "sync note", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync general note", "sync note")
    rebuild(repo)
    results = recall(repo, "sync note", files_in_focus=["src/sync/worker.py"])
    assert results[0]["id"] == "mem-1"


def test_stale_memory_ranked_below_fresh_equal_relevance(repo: Path):
    mk(repo, "mem-1", "worker sync tip", "sync tip", file="src/sync/worker.py")
    mk(repo, "mem-2", "worker sync tip two", "sync tip")
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("x + 1", "x + 2"))  # invalidate mem-1 anchor
    rebuild(repo)
    results = recall(repo, "sync tip")
    assert results[0]["id"] == "mem-2"
    stale = next(r for r in results if r["id"] == "mem-1")
    assert stale["staleness"] == "stale"


def test_k_limits_results(repo: Path):
    for n in range(8):
        mk(repo, f"mem-{n}", f"topic note {n}", "the same topic body")
    rebuild(repo)
    assert len(recall(repo, "topic body", k=3)) == 3


def test_absolute_focus_paths_still_boost(repo: Path):
    mk(repo, "mem-1", "sync focus note", "same body", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync focus note two", "same body")
    rebuild(repo)
    results = recall(
        repo, "focus note", files_in_focus=[str(repo / "src/sync/worker.py")]
    )
    assert results[0]["id"] == "mem-1"
