import io
import json
from pathlib import Path

import pytest

from legendary import cli, service
from legendary.store import load


def remember_one(repo: Path, title: str = "wal deadlock", **kw):
    defaults = dict(
        repo_root=repo,
        type="episode",
        title=title,
        body="busy_timeout",
        anchors=[{"file": "src/sync/worker.py", "symbol": "SyncWorker.run"}],
        tags=[],
        triggers=["sqlite3.OperationalError: database is locked"],
    )
    defaults.update(kw)
    return service.remember(**defaults)


def test_supersedes_deprecates_old_and_links(repo: Path):
    old_id = remember_one(repo)["id"]
    new_id = remember_one(repo, title="wal deadlock v2", supersedes=old_id)["id"]
    old = load(repo, old_id)
    assert old.status == "deprecated"
    assert old.superseded_by == new_id
    assert f"superseded by {new_id}" in old.deprecated_reason


def test_supersedes_unknown_id_raises(repo: Path):
    with pytest.raises(ValueError, match="mem-nope"):
        remember_one(repo, supersedes="mem-nope")


def test_transcript_provenance_round_trips(repo: Path):
    mid = remember_one(repo, transcript="/tmp/session.jsonl")["id"]
    assert load(repo, mid).transcript == "/tmp/session.jsonl"


def surface(repo: Path, monkeypatch, capsys, file: str, session: str = "s1"):
    payload = {
        "session_id": session,
        "tool_name": "Read",
        "tool_input": {"file_path": str(repo / file)},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = cli.main(["surface", "--repo", str(repo)])
    return code, capsys.readouterr().out


def test_surface_emits_additional_context(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    code, out = surface(repo, monkeypatch, capsys, "src/sync/worker.py")
    assert code == 0
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "wal deadlock" in ctx
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_surface_flags_stale_memories(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    p = repo / "src/sync/worker.py"
    p.write_text(p.read_text().replace("retries: int = 3", "retries: int = 8"))
    _, out = surface(repo, monkeypatch, capsys, "src/sync/worker.py")
    assert "stale" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_surface_dedupes_within_session(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    surface(repo, monkeypatch, capsys, "src/sync/worker.py", session="s2")
    _, out2 = surface(repo, monkeypatch, capsys, "src/sync/worker.py", session="s2")
    assert out2.strip() == ""


def test_surface_new_session_resurfaces(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    surface(repo, monkeypatch, capsys, "src/sync/worker.py", session="s3")
    _, out = surface(repo, monkeypatch, capsys, "src/sync/worker.py", session="s4")
    assert out.strip() != ""


def test_surface_unanchored_file_silent(repo: Path, monkeypatch, capsys):
    remember_one(repo)
    _, out = surface(repo, monkeypatch, capsys, ".gitignore")
    assert out.strip() == ""


def test_surface_garbage_stdin_exits_zero(repo: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert cli.main(["surface", "--repo", str(repo)]) == 0
