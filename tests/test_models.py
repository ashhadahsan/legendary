from datetime import datetime, timezone

import pytest

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


def round_trip(mem: Memory) -> Memory:
    return Memory.from_markdown(mem.to_markdown())


def test_round_trip_body_containing_hrule():
    mem = make_memory().model_copy(update={"body": "before\n\n---\n\nafter"})
    assert round_trip(mem) == mem


def test_round_trip_deprecated_memory():
    mem = make_memory().model_copy(
        update={
            "status": "deprecated",
            "deprecated_reason": "superseded by busy_timeout",
        }
    )
    text = mem.to_markdown()
    assert "status: deprecated" in text
    assert Memory.from_markdown(text) == mem


def test_active_memory_omits_deprecated_reason_from_frontmatter():
    assert "deprecated_reason" not in make_memory().to_markdown()


def test_round_trip_title_ending_in_separator():
    mem = make_memory().model_copy(update={"title": "Deprecated approach ---"})
    assert round_trip(mem) == mem


def test_round_trip_tag_containing_separator():
    mem = make_memory().model_copy(update={"tags": ["x---", "y"]})
    assert round_trip(mem) == mem


def test_round_trip_deprecated_reason_containing_separator_line():
    mem = make_memory().model_copy(
        update={"status": "deprecated", "deprecated_reason": "old\n---\nnew"}
    )
    assert round_trip(mem) == mem


def test_from_markdown_rejects_text_without_frontmatter():
    with pytest.raises(ValueError, match="not a frontmatter markdown memory"):
        Memory.from_markdown("just a body, no frontmatter\n")


def test_from_markdown_rejects_unterminated_frontmatter():
    with pytest.raises(ValueError, match="unterminated frontmatter"):
        Memory.from_markdown("---\nid: mem-x\ntype: decision\n")


def test_from_markdown_rejects_non_mapping_frontmatter():
    with pytest.raises(ValueError, match="frontmatter is not a mapping"):
        Memory.from_markdown("---\n- a\n- b\n---\nbody\n")


def test_legacy_types_coerce_to_decision():
    # v0.1 stores may contain convention/reference; they must load, not vanish
    for legacy in ("convention", "reference"):
        m = Memory(
            id="mem-legacy",
            type=legacy,
            title="old memory",
            body="body",
            created=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        assert m.type == "decision"


def test_triggers_round_trip():
    m = Memory(
        id="mem-trig",
        type="episode",
        title="locked db",
        body="body",
        created=datetime(2026, 8, 1, tzinfo=timezone.utc),
        triggers=["sqlite3.OperationalError: database is locked"],
    )
    loaded = Memory.from_markdown(m.to_markdown())
    assert loaded.triggers == ["sqlite3.OperationalError: database is locked"]
