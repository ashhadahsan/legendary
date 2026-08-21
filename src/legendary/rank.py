"""Recall: FTS search -> staleness check -> weighted ranking."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from legendary import index as idx
from legendary.stale import check_memory, worst_verdict
from legendary.store import load

# Fixed weights. Recency is deliberately absent: an old memory whose anchor
# still hashes fresh SURVIVED - recency would double-penalize durability, and
# staleness already measures drift. Config tunables were deleted with it:
# nobody tunes four floats over a store of a few dozen memories.
WEIGHTS = {"fts": 2.0, "overlap": 1.5, "stale": 1.0}
_STALE_PENALTY = {"fresh": 0.0, "stale": 0.5, "orphaned": 0.8}


def _normalize_focus(repo_root: Path, files_in_focus: Optional[list[str]]) -> set[str]:
    """Hosts pass absolute paths; anchors store repo-relative posix paths.
    Exact string intersection between the two silently loses the overlap
    boost, so normalize before matching."""
    focus: set[str] = set()
    root = repo_root.resolve()
    for f in files_in_focus or []:
        p = Path(f)
        if p.is_absolute():
            try:
                focus.add(p.resolve().relative_to(root).as_posix())
                continue
            except ValueError:
                pass  # outside the repo: keep the raw string as a last resort
        focus.add(p.as_posix())
    return focus


def recall(
    repo_root: Path,
    query: str,
    files_in_focus: Optional[list[str]] = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Return top-k memories as dicts with staleness flags and anchor citations."""
    focus = _normalize_focus(repo_root, files_in_focus)
    # fetch a wider candidate pool than k: ranking reorders by staleness and
    # focus overlap, so the FTS top-k is not the final top-k
    hits = idx.search(repo_root, query, limit=max(50, k * 10))
    if not hits:
        return []
    max_rel = max(rel for _, rel in hits) or 1.0

    results: list[dict[str, Any]] = []
    for memory_id, rel in hits:
        m = load(repo_root, memory_id)
        if m is None or m.status != "active":
            continue
        verdicts = check_memory(repo_root, m.anchors)
        worst = worst_verdict(verdicts)
        anchor_files = {a.file for a in m.anchors}
        overlap = 1.0 if focus & anchor_files else 0.0
        score = (
            WEIGHTS["fts"] * (rel / max_rel)
            + WEIGHTS["overlap"] * overlap
            - WEIGHTS["stale"] * _STALE_PENALTY[worst]
        )
        results.append(
            {
                "id": m.id,
                "type": m.type,
                "title": m.title,
                "body": m.body,
                "tags": m.tags,
                "staleness": worst,
                "anchors": [
                    {**a.model_dump(exclude_none=True), "staleness": v}
                    for a, v in zip(m.anchors, verdicts)
                ],
                "score": round(score, 4),
            }
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]
