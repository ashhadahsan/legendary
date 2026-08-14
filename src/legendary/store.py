"""Canonical markdown store under <repo>/.legendary/memories/."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from legendary.models import Memory


def legendary_dir(repo_root: Path) -> Path:
    return repo_root / ".legendary"


def memories_dir(repo_root: Path) -> Path:
    return legendary_dir(repo_root) / "memories"


def _path(repo_root: Path, memory_id: str) -> Path:
    return memories_dir(repo_root) / f"{memory_id}.md"


def save(repo_root: Path, memory: Memory) -> Path:
    d = memories_dir(repo_root)
    d.mkdir(parents=True, exist_ok=True)
    path = _path(repo_root, memory.id)
    path.write_text(memory.to_markdown())
    return path


def load(repo_root: Path, memory_id: str) -> Optional[Memory]:
    path = _path(repo_root, memory_id)
    if not path.exists():
        return None
    return Memory.from_markdown(path.read_text())


def load_all(repo_root: Path) -> list[Memory]:
    d = memories_dir(repo_root)
    if not d.exists():
        return []
    out: list[Memory] = []
    for path in sorted(d.glob("*.md")):
        try:
            out.append(Memory.from_markdown(path.read_text()))
        except Exception as exc:  # malformed file: warn, never crash recall
            print(f"legendary: skipping malformed {path.name}: {exc}", file=sys.stderr)
    return out


def delete(repo_root: Path, memory_id: str) -> None:
    _path(repo_root, memory_id).unlink(missing_ok=True)
