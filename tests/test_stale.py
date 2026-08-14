from pathlib import Path

from legendary.anchor import resolve_and_hash
from legendary.models import Anchor
from legendary.stale import check_anchor, worst_verdict


def anchored(repo: Path, symbol: str = "SyncWorker.run") -> Anchor:
    return resolve_and_hash(repo, Anchor(file="src/sync/worker.py", symbol=symbol))


def test_fresh_when_unchanged(repo: Path):
    assert check_anchor(repo, anchored(repo)) == "fresh"


def test_fresh_survives_whitespace_only_changes(repo: Path):
    a = anchored(repo)
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("    def run", "\n    def run"))
    assert check_anchor(repo, a) == "fresh"


def test_stale_when_region_changed(repo: Path):
    a = anchored(repo)
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("retries: int = 3", "retries: int = 5"))
    assert check_anchor(repo, a) == "stale"


def test_fresh_when_symbol_moved_but_unchanged(repo: Path):
    a = anchored(repo)
    p = repo / "src/sync/worker.py"
    p.write_text("# a leading comment\n\n" + p.read_text())
    assert check_anchor(repo, a) == "fresh"  # re-resolved by symbol, content same


def test_orphaned_when_file_deleted(repo: Path):
    a = anchored(repo)
    (repo / "src/sync/worker.py").unlink()
    assert check_anchor(repo, a) == "orphaned"


def test_orphaned_when_symbol_removed_falls_back_then_detects(repo: Path):
    a = anchored(repo)
    p = repo / "src/sync/worker.py"
    p.write_text("def helper(x):\n    return x\n")
    # symbol gone -> falls back to stored lines/file, content differs -> stale
    assert check_anchor(repo, a) == "stale"


def test_anchor_without_hash_is_fresh(repo: Path):
    # hand-written anchor with no hash: nothing to compare, treat as fresh
    assert check_anchor(repo, Anchor(file="src/sync/worker.py")) == "fresh"


def test_worst_verdict_ordering():
    assert worst_verdict([]) == "fresh"
    assert worst_verdict(["fresh", "stale"]) == "stale"
    assert worst_verdict(["stale", "orphaned", "fresh"]) == "orphaned"
