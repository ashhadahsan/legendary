#!/usr/bin/env python3
"""Aggregate bench/results/*.json (v2 schema). Reports every run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
ARM_ORDER = ["baseline", "legendary"]


def main() -> int:
    runs: dict[str, list[dict]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        rec = json.loads(path.read_text())
        if "s2_quirk_hits" not in rec:
            continue  # v1-schema result, retracted; kept in git, not aggregated
        runs.setdefault(rec["arm"], []).append(rec)
    if not runs:
        print("no v2 results yet - run run_bench.py first")
        return 1

    print(
        "| arm | n | excluded (activation) | median s2 cost | median s2 turns "
        "| s2 hit the quirk | s2 correct |"
    )
    print("|---|---|---|---|---|---|---|")
    for arm in ARM_ORDER:
        rs = runs.get(arm, [])
        if not rs:
            continue
        ok = [r for r in rs if not r["activation_failures"]]
        excluded = len(rs) - len(ok)
        if not ok:
            print(f"| {arm} | 0 | {excluded} | - | - | - | - |")
            continue
        costs = [r["session_2"].get("cost_usd") or 0 for r in ok]
        turns = [r["session_2"].get("num_turns") or 0 for r in ok]
        quirk = sum(1 for r in ok if r["s2_quirk_hits"] > 0)
        correct = sum(1 for r in ok if r["s2_correct"])
        print(
            f"| {arm} | {len(ok)} | {excluded} | "
            f"${statistics.median(costs):.2f} "
            f"(range {min(costs):.2f}-{max(costs):.2f}) | "
            f"{statistics.median(turns):.0f} | {quirk}/{len(ok)} | "
            f"{correct}/{len(ok)} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
