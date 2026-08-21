import io
import json
from pathlib import Path

from legendary import cli, service


def seed_episode(repo: Path):
    return service.remember(
        repo_root=repo,
        type="episode",
        title="deferred BEGIN deadlocks",
        body="Use BEGIN IMMEDIATE; busy_timeout cannot fix a write-write conflict.",
        anchors=[{"file": "src/sync/worker.py"}],
        triggers=["sqlite3.OperationalError: database is locked"],
    )["id"]


def guard(repo: Path, monkeypatch, capsys, output: str, session: str = "g1"):
    payload = {
        "session_id": session,
        "tool_name": "Bash",
        "tool_response": {"stdout": output, "stderr": ""},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = cli.main(["guard", "--repo", str(repo)])
    return code, capsys.readouterr().out


def test_guard_injects_on_matching_error(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    code, out = guard(
        repo,
        monkeypatch,
        capsys,
        "FAILED tests/x.py - sqlite3.OperationalError: database is locked",
    )
    assert code == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PostToolUse"
    assert "BEGIN IMMEDIATE" in payload["additionalContext"]


def test_guard_silent_on_unrelated_output(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    _, out = guard(repo, monkeypatch, capsys, "3 passed in 0.12s")
    assert out.strip() == ""


def test_guard_dedupes_within_session(repo: Path, monkeypatch, capsys):
    seed_episode(repo)
    err = "sqlite3.OperationalError: database is locked"
    guard(repo, monkeypatch, capsys, err, session="g2")
    _, out2 = guard(repo, monkeypatch, capsys, err, session="g2")
    assert out2.strip() == ""


def test_guard_garbage_stdin_exits_zero(repo: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert cli.main(["guard", "--repo", str(repo)]) == 0
