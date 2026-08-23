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


def test_guard_and_surface_use_separate_caches(repo: Path, monkeypatch, capsys):
    """Sharing one cache made the two channels indistinguishable in analysis -
    a benchmark claim had to be withdrawn because of it."""
    seed_episode(repo)
    guard(
        repo, monkeypatch, capsys, "sqlite3.OperationalError: database is locked", "s9"
    )
    guarded = list((repo / ".legendary").glob(".guarded-*"))
    surfaced = list((repo / ".legendary").glob(".surfaced-*"))
    assert guarded, "guard must write its own cache"
    assert not surfaced, "guard must not write surface's cache"


def test_guard_does_not_suppress_surface_for_same_memory(
    repo: Path, monkeypatch, capsys
):
    """Separate caches also mean a memory pushed by one channel can still be
    delivered by the other - they answer different questions."""
    import io as _io
    import json as _json

    seed_episode(repo)
    guard(
        repo, monkeypatch, capsys, "sqlite3.OperationalError: database is locked", "s10"
    )
    payload = {
        "session_id": "s10",
        "tool_name": "Read",
        "tool_input": {"file_path": str(repo / "src/sync/worker.py")},
    }
    monkeypatch.setattr("sys.stdin", _io.StringIO(_json.dumps(payload)))
    cli.main(["surface", "--repo", str(repo)])
    assert capsys.readouterr().out.strip() != ""


def seed_with_trigger(repo: Path, trigger: str) -> str:
    return service.remember(
        repo_root=repo,
        type="episode",
        title="quoted trigger episode",
        body="Send amounts as decimal strings.",
        anchors=[{"file": "src/sync/worker.py"}],
        triggers=[trigger],
    )["id"]


def test_guard_matches_trigger_containing_double_quotes(repo, monkeypatch, capsys):
    """json.dumps escapes quotes, so a quoted trigger could never match output
    that verbatim contained it. Agents naturally write quoted triggers."""
    seed_with_trigger(repo, 'response {"status": "accepted"}')
    _, out = guard(
        repo, monkeypatch, capsys, 'server said: response {"status": "accepted"}', "q1"
    )
    assert out.strip(), "a trigger containing a quote must still match"


def test_guard_matches_trigger_with_brackets_and_parens(repo, monkeypatch, capsys):
    seed_with_trigger(repo, 'server_totals()["batch"]')
    _, out = guard(
        repo, monkeypatch, capsys, 'assert server_totals()["batch"] == 25.0', "q2"
    )
    assert out.strip(), "a trigger with brackets and quotes must match"


def test_guard_matches_trigger_spanning_a_newline(repo, monkeypatch, capsys):
    seed_with_trigger(repo, "Traceback (most recent call last):\n  File")
    _, out = guard(
        repo,
        monkeypatch,
        capsys,
        'Traceback (most recent call last):\n  File "x.py", line 1',
        "q3",
    )
    assert out.strip(), "a multiline trigger must match"


def test_guard_still_silent_on_unrelated_output_after_fix(repo, monkeypatch, capsys):
    seed_with_trigger(repo, 'response {"status": "accepted"}')
    _, out = guard(repo, monkeypatch, capsys, "everything is fine, 5 passed", "q4")
    assert out.strip() == "", "no false positives"


def test_test_name_trigger_warns_but_still_saves(repo: Path):
    r = service.remember(
        repo_root=repo,
        type="episode",
        title="keyed on a test name",
        body="b",
        anchors=[],
        triggers=["test_billing_reconciliation"],
    )
    assert r["id"], "the memory must still be saved"
    assert any("test name" in w for w in r["trigger_warnings"])


def test_numeric_trigger_warns(repo: Path):
    r = service.remember(
        repo_root=repo,
        type="episode",
        title="keyed on numbers",
        body="b",
        anchors=[],
        triggers=["assert 0.0 == 25.0"],
    )
    assert any("specific numbers" in w for w in r["trigger_warnings"])


def test_invariant_trigger_does_not_warn(repo: Path):
    r = service.remember(
        repo_root=repo,
        type="episode",
        title="keyed on the exception",
        body="b",
        anchors=[],
        triggers=["sqlite3.OperationalError: database is locked"],
    )
    assert "trigger_warnings" not in r


def test_guard_writes_an_audit_record(repo: Path, monkeypatch, capsys):
    """Hook output never appears in the agent transcript, so delivery is
    otherwise unobservable - this log is the only evidence a hook fired."""
    import json as _json

    mid = seed_episode(repo)
    guard(
        repo, monkeypatch, capsys, "sqlite3.OperationalError: database is locked", "a1"
    )
    log = repo / ".legendary" / ".injections.jsonl"
    assert log.exists()
    rec = _json.loads(log.read_text().strip().splitlines()[-1])
    assert rec["hook"] == "guard"
    assert rec["session_id"] == "a1"
    assert mid in rec["memory_ids"]
    assert rec["triggers"] == ["sqlite3.OperationalError: database is locked"]
    assert rec["ts"]


def test_surface_writes_an_audit_record(repo: Path, monkeypatch, capsys):
    import io as _io
    import json as _json

    service.remember(
        repo_root=repo,
        type="decision",
        title="worker rule",
        body="b",
        anchors=[{"file": "src/sync/worker.py"}],
    )
    payload = {
        "session_id": "a2",
        "tool_name": "Read",
        "tool_input": {"file_path": str(repo / "src/sync/worker.py")},
    }
    monkeypatch.setattr("sys.stdin", _io.StringIO(_json.dumps(payload)))
    cli.main(["surface", "--repo", str(repo)])
    capsys.readouterr()
    rec = _json.loads(
        (repo / ".legendary" / ".injections.jsonl").read_text().strip().splitlines()[-1]
    )
    assert rec["hook"] == "surface"
    assert rec["file"] == "src/sync/worker.py"
    assert rec["memory_ids"]


def test_audit_failure_never_breaks_the_hook(repo: Path, monkeypatch, capsys):
    """A broken audit log must not break the agent, so _audit swallows errors
    and guard must still deliver its injection."""
    seed_episode(repo)

    def explode(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", explode)
    cli._audit(repo, "guard", "s", ["mem-x"])  # must not raise
    monkeypatch.undo()

    code, out = guard(
        repo, monkeypatch, capsys, "sqlite3.OperationalError: database is locked", "a3"
    )
    assert code == 0 and out.strip(), "the hook still delivers when auditing fails"


def test_render_survives_a_memory_with_no_anchors(repo: Path, monkeypatch, capsys):
    service.remember(
        repo_root=repo,
        type="episode",
        title="unanchored",
        body="b",
        anchors=[],
        triggers=["some invariant error"],
    )
    _, out = guard(repo, monkeypatch, capsys, "some invariant error here", "r3")
    assert "unanchored" in json.loads(out)["hookSpecificOutput"]["additionalContext"]
