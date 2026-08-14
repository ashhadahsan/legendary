from datetime import datetime, timezone

from legendary.models import Anchor, Memory


def make_memory() -> Memory:
    return Memory(
        id="mem-a1b2c3d4",
        type="episode",
        title="Retry logic breaks under WAL",
        body="Tried transactions (attempt 1) - deadlocks under WAL.\n\nWorking approach: busy_timeout.",
        created=datetime(2026, 8, 14, 15, 30, tzinfo=timezone.utc),
        source="agent",
        status="active",
        anchors=[
            Anchor(
                file="src/sync/worker.py",
                symbol="SyncWorker.run",
                lines=(120, 164),
                commit="8fa2c31",
                content_hash="sha256:9f8e",
            )
        ],
        tags=["sqlite", "concurrency"],
    )


def test_markdown_round_trip():
    mem = make_memory()
    text = mem.to_markdown()
    loaded = Memory.from_markdown(text)
    assert loaded == mem


def test_markdown_has_frontmatter_and_body():
    text = make_memory().to_markdown()
    assert text.startswith("---\n")
    assert "Working approach: busy_timeout." in text
    assert "id: mem-a1b2c3d4" in text


def test_new_id_is_deterministic():
    created = datetime(2026, 8, 14, tzinfo=timezone.utc)
    a = Memory.new_id("some title", created)
    b = Memory.new_id("some title", created)
    c = Memory.new_id("other title", created)
    assert a == b
    assert a != c
    assert a.startswith("mem-") and len(a) == 4 + 8


def test_defaults():
    mem = Memory(
        id="mem-x",
        type="decision",
        title="t",
        body="b",
        created=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    assert mem.source == "agent"
    assert mem.status == "active"
    assert mem.anchors == []
    assert mem.tags == []
    assert mem.deprecated_reason is None
