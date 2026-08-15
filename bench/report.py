#!/usr/bin/env python3
"""Aggregate bench/results/*.json into a markdown table. Reports every run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
ARM_ORDER = ["baseline", "graphify", "legendary", "both"]


def main() -> int:
    runs: dict[str, list[dict]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        rec = json.loads(path.read_text())
        runs.setdefault(rec["arm"], []).append(rec)
    if not runs:
        print("no results yet - run run_bench.py first")
        return 1

    print("| arm | n | median tokens | median cost | repeated failure | correct |")
    print("|---|---|---|---|---|---|")
    for arm in ARM_ORDER:
        rs = runs.get(arm)
        if not rs:
            continue
        toks = [r["tokens_total"] for r in rs]
        costs = [r["cost_usd"] for r in rs]
        rf = sum(1 for r in rs if r["repeated_failure"])
        ok = sum(1 for r in rs if r["correct"])
        print(
            f"| {arm} | {len(rs)} | {statistics.median(toks):,.0f} "
            f"(range {min(toks):,}-{max(toks):,}) | "
            f"${statistics.median(costs):.2f} | {rf}/{len(rs)} | {ok}/{len(rs)} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
