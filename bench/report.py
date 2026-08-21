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


def _table(runs: dict[str, list[dict]], label: str) -> None:
    print(f"\n### {label}\n")
    print(
        "| arm | n | excluded | median s2 rediscoveries | s2 hit at all | "
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
            print(f"| {arm} | 0 | {excluded} | - | - | - | - | - |")
            continue
        hits = [r["s2_quirk_hits"] for r in ok]
        costs = [r["session_2"].get("cost_usd") or 0 for r in ok]
        turns = [r["session_2"].get("num_turns") or 0 for r in ok]
        print(
            f"| {arm} | {len(ok)} | {excluded} | "
            f"**{statistics.median(hits):.1f}** (range {min(hits)}-{max(hits)}) | "
            f"{sum(1 for h in hits if h > 0)}/{len(ok)} | "
            f"${statistics.median(costs):.2f} | {statistics.median(turns):.0f} | "
            f"{sum(1 for r in ok if r['s2_correct'])}/{len(ok)} |"
        )


def main() -> int:
    by_scenario: dict[str, dict[str, list[dict]]] = {}
    pooled: dict[str, list[dict]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        rec = json.loads(path.read_text())
        if "s2_quirk_hits" not in rec:
            continue  # v1-schema result, retracted; kept in git, not aggregated
        scen = rec.get("scenario", "opaque_service")
        by_scenario.setdefault(scen, {}).setdefault(rec["arm"], []).append(rec)
        pooled.setdefault(rec["arm"], []).append(rec)
    if not pooled:
        print("no v2 results yet - run run_bench.py first")
        return 1
    # every scenario is published, whether or not it favours legendary
    for scen in sorted(by_scenario):
        _table(by_scenario[scen], scen)
    if len(by_scenario) > 1:
        _table(pooled, "pooled (all scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
