"""Recall: FTS search -> staleness check -> weighted ranking."""

from __future__ import annotations

import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from legendary import index as idx
from legendary.stale import check_memory, worst_verdict
from legendary.store import load

# defaults (spec 3.4); overridden per-repo by [rank] in .legendary/config.toml
WEIGHTS = {"fts": 2.0, "overlap": 1.5, "recency": 0.5, "stale": 1.0}
_STALE_PENALTY = {"fresh": 0.0, "stale": 0.5, "orphaned": 0.8}
_RECENCY_HALF_LIFE_DAYS = 30.0


def _load_weights(repo_root: Path) -> dict[str, float]:
    """Merge [rank] w_* keys from config.toml over the defaults."""
    weights = dict(WEIGHTS)
    cfg = repo_root / ".legendary" / "config.toml"
    if not cfg.is_file():
        return weights
    try:
        rank_cfg = tomllib.loads(cfg.read_text()).get("rank", {})
    except (tomllib.TOMLDecodeError, OSError):
        return weights  # malformed config never breaks recall
    for key in weights:
        val = rank_cfg.get(f"w_{key}")
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            weights[key] = float(val)
    return weights


def recall(
    repo_root: Path,
    query: str,
    files_in_focus: Optional[list[str]] = None,
    k: int = 5,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Return top-k memories as dicts with staleness flags and anchor citations."""
    now = now or datetime.now(timezone.utc)
    weights = _load_weights(repo_root)
    focus = set(files_in_focus or [])
    # fetch a wider candidate pool than k: ranking reorders by staleness,
    # focus overlap, and recency, so the FTS top-k is not the final top-k
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
        age_days = max(0.0, (now - m.created).total_seconds() / 86400.0)
        recency = math.exp(-age_days / _RECENCY_HALF_LIFE_DAYS)
        score = (
            weights["fts"] * (rel / max_rel)
            + weights["overlap"] * overlap
            + weights["recency"] * recency
            - weights["stale"] * _STALE_PENALTY[worst]
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
