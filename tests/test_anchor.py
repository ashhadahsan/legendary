from pathlib import Path

import pytest

from legendary.anchor import (
    hash_text,
    normalize,
    region_text,
    resolve_and_hash,
)
from legendary.models import Anchor


def test_normalize_strips_whitespace_noise():
    a = "def f():\n    return 1\n"
    b = "def f():\n        return 1\n\n"
    assert normalize(a) == normalize(b)


def test_hash_text_is_stable_and_prefixed():
    h = hash_text("hello")
    assert h.startswith("sha256:")
    assert h == hash_text("hello")


def test_region_text_symbol_python_method(repo: Path):
    anchor = Anchor(file="src/sync/worker.py", symbol="SyncWorker.run")
    text, lines = region_text(repo, anchor)
    assert "def run(self" in text
    assert "_sync_once" in text
    assert "def helper" not in text
    assert lines[0] >= 1 and lines[1] > lines[0]


def test_region_text_symbol_top_level_function(repo: Path):
    text, _ = region_text(repo, Anchor(file="src/sync/worker.py", symbol="helper"))
    assert text.startswith("def helper")


def test_region_text_lines(repo: Path):
    text, lines = region_text(repo, Anchor(file="src/sync/worker.py", lines=(1, 2)))
    assert "class SyncWorker" in text
    assert lines == (1, 2)


def test_region_text_whole_file(repo: Path):
    text, _ = region_text(repo, Anchor(file="src/sync/worker.py"))
    assert "class SyncWorker" in text and "def helper" in text


def test_region_text_missing_file_returns_none(repo: Path):
    assert region_text(repo, Anchor(file="nope.py")) is None


def test_region_text_unresolvable_symbol_falls_back_to_file(repo: Path):
    anchor = Anchor(file="src/sync/worker.py", symbol="DoesNotExist")
    text, _ = region_text(repo, anchor)
    assert "class SyncWorker" in text  # whole-file fallback


def test_resolve_and_hash_fills_fields(repo: Path):
    anchor = resolve_and_hash(repo, Anchor(file="src/sync/worker.py", symbol="SyncWorker.run"))
    assert anchor.content_hash and anchor.content_hash.startswith("sha256:")
    assert anchor.commit and len(anchor.commit) >= 7
    assert anchor.lines is not None  # resolved span recorded for fallback


def test_resolve_and_hash_missing_file_raises(repo: Path):
    with pytest.raises(FileNotFoundError):
        resolve_and_hash(repo, Anchor(file="nope.py"))


def test_resolve_and_hash_unresolvable_symbol_raises(repo: Path):
    # write path is strict (spec 3.2) even though region_text is lenient
    with pytest.raises(ValueError, match="line range"):
        resolve_and_hash(repo, Anchor(file="src/sync/worker.py", symbol="DoesNotExist"))


def test_region_text_out_of_range_lines_fall_back_to_file(repo: Path):
    # file shrank below the stored range -> whole file, NOT None
    text, _ = region_text(repo, Anchor(file="src/sync/worker.py", lines=(900, 950)))
    assert "class SyncWorker" in text
