"""Recall-time staleness verdicts for anchors."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from legendary.anchor import hash_text, region_text
from legendary.models import Anchor

Verdict = Literal["fresh", "stale", "orphaned"]
_SEVERITY: dict[Verdict, int] = {"fresh": 0, "stale": 1, "orphaned": 2}


def check_anchor(repo_root: Path, anchor: Anchor) -> Verdict:
    resolved = region_text(repo_root, anchor)
    if resolved is None:
        return "orphaned"
    if anchor.content_hash is None:
        return "fresh"  # nothing to compare against
    text, _ = resolved
    return "fresh" if hash_text(text) == anchor.content_hash else "stale"


def check_memory(repo_root: Path, anchors: list[Anchor]) -> list[Verdict]:
    return [check_anchor(repo_root, a) for a in anchors]


def worst_verdict(verdicts: list[Verdict]) -> Verdict:
    if not verdicts:
        return "fresh"
    return max(verdicts, key=lambda v: _SEVERITY[v])
