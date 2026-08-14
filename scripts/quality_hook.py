#!/usr/bin/env python3
"""Claude Code PostToolUse hook: format, lint, and type-check edited python.

Reads the hook payload on stdin. Exit 2 tells Claude the tool call had a
problem and feeds stderr back to it, so the agent fixes the issue in-loop
instead of discovering it at commit time.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # not hook-invoked; stay silent
    path_str = (payload.get("tool_input") or {}).get("file_path")
    if not path_str:
        return 0
    path = Path(path_str)
    if path.suffix != ".py" or not path.is_file():
        return 0

    run(["uv", "run", "ruff", "format", str(path)])
    run(["uv", "run", "ruff", "check", "--fix", str(path)])

    problems: list[str] = []
    code, out = run(["uv", "run", "ruff", "check", str(path)])
    if code != 0 and out:
        problems.append(out)
    # mypy is configured over the package; only report lines about this file
    code, out = run(["uv", "run", "mypy"])
    if code != 0:
        relevant = [ln for ln in out.splitlines() if path.name in ln]
        if relevant:
            problems.append("\n".join(relevant))

    if problems:
        print("legendary quality gate failed:\n" + "\n".join(problems), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
