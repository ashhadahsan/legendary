import json
from pathlib import Path

from legendary import cli, service


def run_cli(*args, cwd: Path, capsys) -> tuple[int, str]:
    code = cli.main([*map(str, args), "--repo", str(cwd)])
    return code, capsys.readouterr().out


def test_init_scaffolds_and_installs_hooks(repo: Path, capsys):
    code, out = run_cli("init", cwd=repo, capsys=capsys)
    assert code == 0
    assert (repo / ".legendary" / "memories").is_dir()
    assert ".legendary/index.db" in (repo / ".gitignore").read_text()
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]
    assert any(
        "legendary surface" in h["hooks"][0]["command"] for h in hooks["PreToolUse"]
    )
    assert any(
        "legendary guard" in h["hooks"][0]["command"] for h in hooks["PostToolUse"]
    )
    assert "mcpServers" in out  # MCP remains available as the printed add-on


def test_init_twice_is_safe_and_idempotent(repo: Path, capsys):
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    assert (repo / ".gitignore").read_text().count(".legendary/index.db") == 1
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    assert len(settings["hooks"]["PreToolUse"]) == 1  # not duplicated


def test_init_preserves_existing_user_hooks(repo: Path, capsys):
    claude = repo / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": "echo mine"}],
                        }
                    ]
                },
                "env": {"FOO": "1"},
            }
        )
    )
    run_cli("init", cwd=repo, capsys=capsys)
    settings = json.loads((claude / "settings.json").read_text())
    assert settings["env"] == {"FOO": "1"}  # untouched
    commands = [h["hooks"][0]["command"] for h in settings["hooks"]["PreToolUse"]]
    assert "echo mine" in commands
    assert any("legendary surface" in c for c in commands)


def test_init_outside_git_repo_fails(tmp_path: Path, capsys):
    code, _ = run_cli("init", cwd=tmp_path, capsys=capsys)
    assert code == 1


def seed(repo):
    service.remember(
        repo_root=repo,
        type="episode",
        title="wal deadlock",
        body="busy_timeout",
        anchors=[{"file": "src/sync/worker.py"}],
        tags=["sqlite"],
        triggers=["sqlite3.OperationalError: database is locked"],
    )


def test_search_outputs_json(repo: Path, capsys):
    seed(repo)
    code, out = run_cli("search", "wal deadlock", cwd=repo, capsys=capsys)
    assert code == 0
    assert json.loads(out)[0]["title"] == "wal deadlock"


def test_reindex_reports_count(repo: Path, capsys):
    seed(repo)
    (repo / ".legendary" / "index.db").unlink()
    code, out = run_cli("reindex", cwd=repo, capsys=capsys)
    assert code == 0 and "1" in out


def test_doctor_reports_stale(repo: Path, capsys):
    seed(repo)
    p = repo / "src/sync/worker.py"
    p.write_text("totally different\n")
    code, out = run_cli("doctor", cwd=repo, capsys=capsys)
    assert code == 0
    assert "stale" in out
