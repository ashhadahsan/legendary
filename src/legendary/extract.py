"""Auto-extract memories from a session transcript using `claude -p` (headless)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from legendary import service

_MAX_TRANSCRIPT_CHARS = 200_000

_PROMPT = """\
You are a memory extractor for a coding-agent memory system. Below is a coding
session transcript. Extract AT MOST 5 memories worth keeping for future
sessions. Only extract things that are non-obvious and durable:
- decisions: why something is built the way it is
- episodes: an approach that was tried and FAILED, and why
- conventions: team/project practices observed
- references: external docs/tickets mentioned as authoritative

Be conservative: if nothing qualifies, return [].

Reply with ONLY a JSON array. Each element:
{"type": "decision|episode|convention|reference", "title": "...",
 "body": "...", "tags": ["..."],
 "anchors": [{"file": "relative/path.py", "symbol": "Optional.Dotted.Name"}]}

TRANSCRIPT:
%s
"""


def _run_claude(prompt: str) -> str:
    out = subprocess.run(
        ["claude", "-p", prompt], capture_output=True, text=True, timeout=300
    )
    if out.returncode != 0:
        raise RuntimeError(f"claude -p failed: {out.stderr[:500]}")
    return out.stdout


def parse_candidates(raw: str) -> list[dict[str, Any]]:
    """Parse claude output into candidate dicts. Garbage in -> empty list out."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [c for c in data if isinstance(c, dict) and c.get("title")]


def _read_transcript(path: Path) -> str:
    """Best-effort flatten of a Claude Code .jsonl transcript (or plain text)."""
    lines = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            obj = json.loads(line)
            role = obj.get("role") or obj.get("type") or "?"
            content = obj.get("content")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            if content:
                lines.append(f"{role}: {content}")
        except json.JSONDecodeError:
            lines.append(line)
    return "\n".join(lines)[-_MAX_TRANSCRIPT_CHARS:]


def extract_from_transcript(repo_root: Path, transcript_path: Path) -> list[str]:
    """Run extraction; returns list of saved memory ids."""
    try:
        raw = _run_claude(_PROMPT % _read_transcript(transcript_path))
    except FileNotFoundError as exc:
        raise RuntimeError(
            "claude CLI not found - install Claude Code or skip auto-extraction; "
            "legendary's MCP tools work without it"
        ) from exc
    saved: list[str] = []
    for cand in parse_candidates(raw):
        anchors = cand.get("anchors") or []
        try:
            result = service.remember(
                repo_root,
                type=str(cand.get("type") or "reference"),
                title=cand["title"],
                body=cand.get("body", ""),
                anchors=anchors,
                tags=cand.get("tags") or [],
                source="auto-extract",
            )
        except ValueError:
            raw_type = cand.get("type")
            safe_type = (
                raw_type
                if raw_type in ("decision", "episode", "convention", "reference")
                else "reference"
            )
            try:  # bad anchor or type: retry without anchors, safe type
                result = service.remember(
                    repo_root,
                    type=safe_type,
                    title=cand["title"],
                    body=cand.get("body", ""),
                    anchors=[],
                    tags=cand.get("tags") or [],
                    source="auto-extract",
                )
            except ValueError:
                continue  # unsalvageable candidate: drop it
        saved.append(result["id"])
    return saved
