import json
from pathlib import Path

import pytest

from legendary.extract import extract_from_transcript, parse_candidates
from legendary.store import load_all

CLAUDE_OUTPUT = json.dumps(
    [
        {
            "type": "episode",
            "title": "WAL deadlock on retry",
            "body": "Wrapping retries in a transaction deadlocks under WAL.",
            "tags": ["sqlite"],
            "anchors": [{"file": "src/sync/worker.py", "symbol": "SyncWorker.run"}],
        },
        {
            "type": "convention",
            "title": "Use uv for everything",
            "body": "Team runs all python through uv.",
            "tags": [],
            "anchors": [],
        },
    ]
)


def test_parse_candidates_plain_json():
    assert len(parse_candidates(CLAUDE_OUTPUT)) == 2


def test_parse_candidates_strips_code_fences():
    fenced = f"```json\n{CLAUDE_OUTPUT}\n```"
    assert len(parse_candidates(fenced)) == 2


def test_parse_candidates_garbage_returns_empty():
    assert parse_candidates("sorry, I cannot") == []
    assert parse_candidates('{"not": "a list"}') == []


def test_extract_saves_valid_and_skips_bad_anchors(repo: Path, monkeypatch):
    transcript = repo / "t.jsonl"
    transcript.write_text(json.dumps({"role": "user", "content": "fix sync"}) + "\n")

    bad = json.loads(CLAUDE_OUTPUT)
    bad.append(
        {
            "type": "episode",
            "title": "ghost",
            "body": "x",
            "tags": [],
            "anchors": [{"file": "nope.py"}],
        }
    )
    monkeypatch.setattr("legendary.extract._run_claude", lambda prompt: json.dumps(bad))
    saved = extract_from_transcript(repo, transcript)
    assert len(saved) == 3  # bad anchor dropped, memory still saved anchor-less
    memories = {m.title: m for m in load_all(repo)}
    assert memories["ghost"].anchors == []
    assert all(m.source == "auto-extract" for m in memories.values())


def test_extract_claude_missing_raises_clear_error(repo: Path, monkeypatch):
    transcript = repo / "t.jsonl"
    transcript.write_text("{}")

    def boom(prompt):
        raise FileNotFoundError("claude")

    monkeypatch.setattr("legendary.extract._run_claude", boom)
    with pytest.raises(RuntimeError, match="claude CLI not found"):
        extract_from_transcript(repo, transcript)
