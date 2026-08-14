from datetime import datetime, timedelta, timezone
from pathlib import Path

from legendary.anchor import resolve_and_hash
from legendary.index import rebuild
from legendary.models import Anchor, Memory
from legendary.rank import recall
from legendary.store import save

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


def mk(
    repo: Path,
    i: str,
    title: str,
    body: str,
    *,
    file: str | None = None,
    created: datetime = NOW,
) -> Memory:
    anchors = []
    if file:
        anchors = [resolve_and_hash(repo, Anchor(file=file))]
    m = Memory(
        id=i, type="episode", title=title, body=body, created=created, anchors=anchors
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
    results = recall(repo, "sqlite deadlock", now=NOW)
    assert results[0]["id"] == "mem-1"
    assert results[0]["staleness"] == "fresh"
    assert "title" in results[0] and "body" in results[0]


def test_files_in_focus_boosts_anchored_memory(repo: Path):
    mk(repo, "mem-1", "sync worker note", "sync note", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync general note", "sync note")
    rebuild(repo)
    results = recall(repo, "sync note", files_in_focus=["src/sync/worker.py"], now=NOW)
    assert results[0]["id"] == "mem-1"


def test_stale_memory_ranked_below_fresh_equal_relevance(repo: Path):
    mk(repo, "mem-1", "worker sync tip", "sync tip", file="src/sync/worker.py")
    mk(repo, "mem-2", "worker sync tip two", "sync tip")
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("x + 1", "x + 2"))  # invalidate mem-1 anchor
    rebuild(repo)
    results = recall(repo, "sync tip", now=NOW)
    assert results[0]["id"] == "mem-2"
    stale = next(r for r in results if r["id"] == "mem-1")
    assert stale["staleness"] == "stale"


def test_recency_breaks_ties(repo: Path):
    mk(
        repo,
        "mem-1",
        "deploy checklist",
        "deploy steps",
        created=NOW - timedelta(days=300),
    )
    mk(repo, "mem-2", "deploy checklist new", "deploy steps", created=NOW)
    rebuild(repo)
    results = recall(repo, "deploy steps", now=NOW)
    assert results[0]["id"] == "mem-2"


def test_k_limits_results(repo: Path):
    for n in range(8):
        mk(repo, f"mem-{n}", f"topic note {n}", "the same topic body")
    rebuild(repo)
    assert len(recall(repo, "topic body", k=3, now=NOW)) == 3


def test_config_toml_weights_are_applied(repo: Path):
    mk(repo, "mem-1", "sync note one", "sync note", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync note two", "sync note")
    rebuild(repo)
    cfg = repo / ".legendary" / "config.toml"
    cfg.write_text("[rank]\nw_overlap = 0.0\nw_recency = 0.0\n")
    # focus boost disabled -> the anchored memory no longer wins on overlap
    scores = {
        r["id"]: r["score"]
        for r in recall(
            repo, "sync note", files_in_focus=["src/sync/worker.py"], now=NOW
        )
    }
    assert scores["mem-1"] == scores["mem-2"]


def test_malformed_config_falls_back_to_defaults(repo: Path):
    mk(repo, "mem-1", "sync note one", "sync note", file="src/sync/worker.py")
    mk(repo, "mem-2", "sync note two", "sync note")
    rebuild(repo)
    (repo / ".legendary" / "config.toml").write_text("[rank\nthis is not toml")
    results = recall(repo, "sync note", files_in_focus=["src/sync/worker.py"], now=NOW)
    assert results[0]["id"] == "mem-1"  # default overlap boost still applied
