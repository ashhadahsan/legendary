from pathlib import Path

import pytest

from legendary import service
from legendary.store import load


def remember_one(repo: Path, **kw):
    defaults = dict(
        repo_root=repo,
        type="episode",
        title="wal deadlock",
        body="busy_timeout fixes it",
        anchors=[{"file": "src/sync/worker.py", "symbol": "SyncWorker.run"}],
        tags=["sqlite"],
    )
    defaults.update(kw)
    return service.remember(**defaults)


def test_remember_saves_and_indexes(repo: Path):
    result = remember_one(repo)
    mid = result["id"]
    m = load(repo, mid)
    assert m is not None and m.title == "wal deadlock"
    assert m.anchors[0].content_hash is not None
    hits = service.recall(repo, "wal deadlock")
    assert hits and hits[0]["id"] == mid


def test_remember_rejects_bad_anchor_file(repo: Path):
    with pytest.raises(ValueError, match="nope.py"):
        remember_one(repo, anchors=[{"file": "nope.py"}])


def test_remember_rejects_bad_type(repo: Path):
    with pytest.raises(ValueError):
        remember_one(repo, type="wisdom")


def test_list_memories_filters(repo: Path):
    remember_one(repo)
    service.remember(
        repo_root=repo,
        type="convention",
        title="use uv",
        body="always uv",
        anchors=[],
        tags=["tooling"],
    )
    assert len(service.list_memories(repo)) == 2
    assert len(service.list_memories(repo, type="convention")) == 1
    assert len(service.list_memories(repo, tag="sqlite")) == 1
    assert len(service.list_memories(repo, file="src/sync/worker.py")) == 1


def test_deprecate_removes_from_recall(repo: Path):
    mid = remember_one(repo)["id"]
    service.deprecate(repo, mid, reason="superseded")
    m = load(repo, mid)
    assert m.status == "deprecated" and m.deprecated_reason == "superseded"
    assert all(r["id"] != mid for r in service.recall(repo, "wal deadlock"))


def test_deprecate_unknown_id_raises(repo: Path):
    with pytest.raises(ValueError, match="mem-nope"):
        service.deprecate(repo, "mem-nope", reason="x")


def test_stale_report_lists_only_problems(repo: Path):
    remember_one(repo)
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("retries: int = 3", "retries: int = 9"))
    report = service.stale_report(repo)
    assert len(report) == 1
    assert report[0]["staleness"] == "stale"

    p.unlink()
    report = service.stale_report(repo)
    assert report[0]["staleness"] == "orphaned"
