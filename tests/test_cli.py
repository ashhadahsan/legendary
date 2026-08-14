import json
from pathlib import Path

from legendary import cli, service


def run_cli(*args, cwd: Path, capsys) -> tuple[int, str]:
    code = cli.main([*map(str, args), "--repo", str(cwd)])
    return code, capsys.readouterr().out


def test_init_scaffolds(repo: Path, capsys):
    code, out = run_cli("init", cwd=repo, capsys=capsys)
    assert code == 0
    assert (repo / ".legendary" / "memories").is_dir()
    assert (repo / ".legendary" / "config.toml").exists()
    assert ".legendary/index.db" in (repo / ".gitignore").read_text()
    assert "mcpServers" in out  # prints MCP setup snippet
    assert "SessionEnd" in out  # prints hook snippet


def test_init_twice_is_safe(repo: Path, capsys):
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    assert run_cli("init", cwd=repo, capsys=capsys)[0] == 0
    # .gitignore entry not duplicated
    assert (repo / ".gitignore").read_text().count(".legendary/index.db") == 1


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


def test_inject_prints_memories(repo: Path, capsys):
    seed(repo)
    code, out = run_cli("inject", cwd=repo, capsys=capsys)
    assert code == 0
    assert "wal deadlock" in out


def test_inject_empty_repo_prints_nothing(repo: Path, capsys):
    code, out = run_cli("inject", cwd=repo, capsys=capsys)
    assert code == 0
    assert out.strip() == ""
