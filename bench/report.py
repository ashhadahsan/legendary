#!/usr/bin/env python3
"""Aggregate bench/results/*.json (v2 schema). Reports every run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
ARM_ORDER = ["baseline", "legendary"]


def _failures(rec: dict) -> list[str]:
    """Recompute activation from observed use.

    Records written before 2026-08-21 asserted on the init event's tool list,
    which does not enumerate MCP tools - so they carry a spurious
    `mcp_tools_not_offered`. Recomputing here keeps those trials usable
    instead of discarding real data for a harness bug.
    """
    fails = [
        f for f in rec.get("activation_failures", []) if f != "mcp_tools_not_offered"
    ]
    if rec["arm"] == "baseline":
        return fails
    s1, s2 = rec["session_1"], rec["session_2"]
    worked = (
        s1.get("used_recall")
        or s1.get("used_remember")
        or s2.get("used_recall")
        or s2.get("used_remember")
        or rec.get("hook_fired")
    )
    if not worked and "no_legendary_channel_activated" not in fails:
        fails.append("no_legendary_channel_activated")
    return fails


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
        "| arm | n | excluded | median s2 quirk hits | s2 hit at all | "
        "median s2 cost | median s2 turns | s2 correct |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for arm in ARM_ORDER:
        rs = runs.get(arm, [])
        if not rs:
            continue
        ok = [r for r in rs if not _failures(r)]
        excluded = len(rs) - len(ok)
        if not ok:
            print(f"| {arm} | 0 | {excluded} | - | - | - | - |")
            continue
        costs = [r["session_2"].get("cost_usd") or 0 for r in ok]
        turns = [r["session_2"].get("num_turns") or 0 for r in ok]
        # the COUNT is the signal - how many times the agent rediscovered the
        # quirk the hard way. A binary "did it happen" throws that away.
        hits = [r["s2_quirk_hits"] for r in ok]
        quirk_any = sum(1 for h in hits if h > 0)
        correct = sum(1 for r in ok if r["s2_correct"])
        print(
            f"| {arm} | {len(ok)} | {excluded} | "
            f"**{statistics.median(hits):.1f}** "
            f"(range {min(hits)}-{max(hits)}) | "
            f"{quirk_any}/{len(ok)} | "
            f"${statistics.median(costs):.2f} | "
            f"{statistics.median(turns):.0f} | "
            f"{correct}/{len(ok)} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
