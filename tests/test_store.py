from datetime import datetime, timezone
from pathlib import Path

from legendary.models import Memory
from legendary.store import delete, load, load_all, memories_dir, save


def mem(i: str = "mem-00000001", title: str = "t") -> Memory:
    return Memory(
        id=i,
        type="decision",
        title=title,
        body="body",
        created=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def test_save_creates_markdown_file(repo: Path):
    save(repo, mem())
    path = memories_dir(repo) / "mem-00000001.md"
    assert path.exists()
    assert "id: mem-00000001" in path.read_text()


def test_save_then_load_round_trips(repo: Path):
    m = mem()
    save(repo, m)
    assert load(repo, m.id) == m


def test_load_all_skips_malformed_files(repo: Path):
    save(repo, mem("mem-00000001", "one"))
    save(repo, mem("mem-00000002", "two"))
    (memories_dir(repo) / "broken.md").write_text("not a memory at all")
    loaded = load_all(repo)
    assert sorted(m.id for m in loaded) == ["mem-00000001", "mem-00000002"]


def test_load_missing_returns_none(repo: Path):
    assert load(repo, "mem-nope") is None


def test_delete(repo: Path):
    m = mem()
    save(repo, m)
    delete(repo, m.id)
    assert load(repo, m.id) is None
