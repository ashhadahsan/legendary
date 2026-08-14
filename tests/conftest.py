import subprocess
from pathlib import Path

import pytest

SAMPLE_PY = '''\
class SyncWorker:
    """Worker that syncs things."""

    def run(self, retries: int = 3) -> None:
        for attempt in range(retries):
            self._sync_once()

    def _sync_once(self) -> None:
        pass


def helper(x: int) -> int:
    return x + 1
'''


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A temp git repo with one committed python file at src/sync/worker.py."""
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    src = tmp_path / "src" / "sync"
    src.mkdir(parents=True)
    (src / "worker.py").write_text(SAMPLE_PY)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path
