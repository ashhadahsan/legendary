#!/usr/bin/env python3
"""Replay legendary's hooks offline against archived trials. Costs nothing.

`surface` and `guard` are pure functions of (store, hook-input). Every input is
already archived: the memory store in bench/results/artifacts/, and the
session-2 transcript in bench/results/. So we can answer "would a hook have
fired, and when?" without spending a single agent session.

This exists because hook delivery has been unobservable: hook output does not
appear in the agent transcript, and the dedupe caches record only that
something happened, never what or when. The audit log added in cli.py fixes
that going forward; this recovers the answer for trials already run.

Usage:
    uv run python bench/replay_hooks.py [--arm legendary_recall_only]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BENCH = Path(__file__).parent
RESULTS = BENCH / "results"
ARTIFACTS = RESULTS / "artifacts"


def load_store(trial_dir: Path) -> list[dict]:
    """Read the memories a trial actually had, with their triggers and anchors."""
    memories = []
    for md in sorted((trial_dir / ".legendary" / "memories").glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        parts = text.split("---")
        if len(parts) < 3:
            continue
        front = parts[1]

        def field(name: str) -> str | None:
            m = re.search(rf"^{name}: (.+)$", front, re.M)
            return m.group(1).strip().strip("'\"") if m else None

        triggers = (
            re.findall(
                r"^- (.+)$",
                (re.search(r"^triggers:\n((?:- .+\n)+)", front, re.M) or [None, ""])[1],
                re.M,
            )
            if re.search(r"^triggers:", front, re.M)
            else []
        )
        files = re.findall(r"^\s*- file: (\S+)$", front, re.M)
        memories.append(
            {
                "id": field("id") or md.stem,
                "status": field("status") or "active",
                "triggers": [t.strip().strip("'\"") for t in triggers],
                "files": files,
            }
        )
    return memories


def haystack(obj: object) -> str:
    """Mirror of cli._haystack - raw leaf text, not json.dumps."""
    parts: list[str] = []
    stack: list[object] = [obj]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, (list, tuple)):
            stack.extend(v)
        else:
            parts.append(str(v))
    return "\n".join(parts).lower()


def replay(trial_dir: Path, transcript: Path) -> dict:
    """Walk a session-2 transcript, reporting what each hook would have done."""
    memories = [m for m in load_store(trial_dir) if m["status"] == "active"]
    surface_fires: list[int] = []
    guard_fires: list[tuple[int, str]] = []
    turn = 0

    for line in transcript.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        turn += 1
        blob = json.dumps(event)

        # PreToolUse on Read|Edit|Write -> surface matches on exact anchor path
        for m in re.finditer(r'"file_path":\s*"([^"]+)"', blob):
            touched = m.group(1)
            for mem in memories:
                if any(touched.endswith(f) for f in mem["files"]):
                    surface_fires.append(turn)
                    break

        # PostToolUse on Bash -> guard matches stored triggers in the output
        if '"tool_use_id"' in blob or '"tool_result"' in blob or '"stdout"' in blob:
            hay = haystack(event)
            for mem in memories:
                for trig in mem["triggers"]:
                    if trig and trig.lower() in hay:
                        guard_fires.append((turn, trig))
                        break

    return {
        "trial": trial_dir.name,
        "memories": len(memories),
        "triggers": sum(len(m["triggers"]) for m in memories),
        "surface_fires": len(surface_fires),
        "first_surface_turn": surface_fires[0] if surface_fires else None,
        "guard_fires": len(guard_fires),
        "first_guard_turn": guard_fires[0][0] if guard_fires else None,
        "matched_triggers": sorted({t for _, t in guard_fires}),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="legendary_recall_only")
    ap.add_argument("--artifacts", default="legbench-abl")
    args = ap.parse_args()

    root = ARTIFACTS / args.artifacts
    rows = []
    for trial_dir in sorted(root.glob(f"opaque_service-{args.arm}-*")):
        if not trial_dir.is_dir():
            continue
        transcript = RESULTS / f"{trial_dir.name}-session_2.txt"
        if not transcript.exists():
            continue
        rows.append(replay(trial_dir, transcript))

    if not rows:
        print(f"no replayable trials for arm {args.arm!r} in {root}")
        return 1

    print(f"### offline hook replay - {args.arm} (n={len(rows)})\n")
    print("| trial | memories | triggers | surface fires | guard fires | matched |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(
            f"| {r['trial'].split('-')[-1]} | {r['memories']} | {r['triggers']} | "
            f"{r['surface_fires']} | {r['guard_fires']} | "
            f"{', '.join(r['matched_triggers'])[:60] or '-'} |"
        )
    guard_any = sum(1 for r in rows if r["guard_fires"])
    surf_any = sum(1 for r in rows if r["surface_fires"])
    print(f"\nsurface would have fired in {surf_any}/{len(rows)} trials")
    print(f"guard would have fired in   {guard_any}/{len(rows)} trials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
