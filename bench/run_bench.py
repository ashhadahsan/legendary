#!/usr/bin/env python3
"""Run the legendary benchmark across four arms. Publishes raw JSON per trial."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

BENCH = Path(__file__).parent
SCENARIO = BENCH / "scenario"
RESULTS = BENCH / "results"

SESSION_1 = (
    "The concurrency test for sync/worker.py fails. Diagnose and fix it so "
    "`pytest tests/test_sync.py -k worker` passes. Do not modify the tests."
)
SESSION_2 = (
    "The concurrency test for sync/reporter.py fails. Diagnose and fix it so "
    "`pytest tests/test_sync.py -k reporter` passes. Do not modify the tests."
)

# The plausible-but-wrong approach session 1 teaches you to avoid. Keep this
# list identical to the one pre-registered in bench/README.md.
BAD_PATTERNS = ["BEGIN TRANSACTION", 'conn.execute("BEGIN']

# Graphify ships on PyPI as `graphifyy` (the `graphify` name is a different,
# unrelated package). Confirm both invocations with `graphify --help` before
# benchmarking; update these two constants if its CLI differs.
GRAPHIFY_BUILD = ["uvx", "--from", "graphifyy", "graphify", "build", "."]
GRAPHIFY_SERVE = {
    "command": "uvx",
    "args": ["--from", "graphifyy", "graphify", "serve"],
}

ARMS = {
    "baseline": [],
    "graphify": ["graphify"],
    "legendary": ["legendary"],
    "both": ["graphify", "legendary"],
}


def mcp_config(tools: list[str], repo: Path) -> dict:
    servers: dict[str, dict] = {}
    if "legendary" in tools:
        servers["legendary"] = {
            "command": "uvx",
            "args": [
                "--from",
                "legendary-mcp",
                "legendary",
                "mcp",
                "--repo",
                str(repo),
            ],
        }
    if "graphify" in tools:
        servers["graphify"] = {**GRAPHIFY_SERVE, "cwd": str(repo)}
    return {"mcpServers": servers}


def run_session(repo: Path, prompt: str, config_path: Path) -> dict:
    # --dangerously-skip-permissions: headless -p cannot show a prompt, and
    # --permission-mode acceptEdits still blocks Bash and MCP tool calls, so the
    # agent could never run pytest. Safe here: every trial runs in a disposable
    # copy of the fixture under --workdir, never in a real repo.
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        "--max-turns",
        "40",
        # --strict-mcp-config on EVERY arm (baseline included, with an empty
        # server map) so no arm inherits the operator's ambient MCP servers.
        "--mcp-config",
        str(config_path),
        "--strict-mcp-config",
    ]
    started = time.monotonic()
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=1800)
    elapsed = time.monotonic() - started
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "error": (proc.stdout[-2000:] or proc.stderr[-2000:]),
            "duration_s": round(elapsed, 1),
        }
    u = data.get("usage", {})
    return {
        "tokens_total": sum(
            int(u.get(k, 0) or 0)
            for k in (
                "input_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
                "output_tokens",
            )
        ),
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "duration_s": round(elapsed, 1),
        "is_error": data.get("is_error"),
    }


def tests_pass(repo: Path) -> bool:
    proc = subprocess.run(
        ["uv", "run", "--isolated", "--with", "pytest", "pytest", "-q"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.returncode == 0


def repeated_failure(repo: Path) -> bool:
    """Did the agent reintroduce the approach session 1 proved wrong?"""
    # Exclude .legendary/: a memory whose body says "do not use BEGIN
    # TRANSACTION" would otherwise score as a repeated failure, biasing the
    # metric against the very arm being measured.
    diff = subprocess.run(
        ["git", "diff", "--", ".", ":(exclude).legendary"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.lower()
    return any(pat.lower() in diff for pat in BAD_PATTERNS)


def trial(arm: str, index: int, workdir: Path) -> dict:
    repo = workdir / f"{arm}-{index}"
    shutil.copytree(SCENARIO, repo)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=b@b.b",
            "-c",
            "user.name=bench",
            "commit",
            "-qm",
            "scenario",
        ],
        cwd=repo,
        check=True,
    )

    tools = ARMS[arm]
    config_path = repo / ".bench-mcp.json"  # written for every arm, empty for baseline
    config_path.write_text(json.dumps(mcp_config(tools, repo)))
    if "legendary" in tools:
        subprocess.run(
            [
                "uvx",
                "--from",
                "legendary-mcp",
                "legendary",
                "init",
                "--repo",
                str(repo),
            ],
            check=True,
            capture_output=True,
        )
    if "graphify" in tools:
        # Graphify must index the repo before its MCP server can answer anything
        subprocess.run(GRAPHIFY_BUILD, cwd=repo, check=True, capture_output=True)

    s1 = run_session(repo, SESSION_1, config_path)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=b@b.b",
            "-c",
            "user.name=bench",
            "commit",
            "-qm",
            "session1",
            "--allow-empty",
        ],
        cwd=repo,
        check=True,
    )
    s2 = run_session(repo, SESSION_2, config_path)

    return {
        "arm": arm,
        "trial": index,
        "session_1": s1,
        "session_2": s2,
        "tokens_total": (s1.get("tokens_total", 0) or 0)
        + (s2.get("tokens_total", 0) or 0),
        "cost_usd": round((s1.get("cost_usd") or 0) + (s2.get("cost_usd") or 0), 4),
        "duration_s": round(
            (s1.get("duration_s") or 0) + (s2.get("duration_s") or 0), 1
        ),
        "repeated_failure": repeated_failure(repo),
        "correct": tests_pass(repo),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("-n", "--trials", type=int, default=5)
    ap.add_argument(
        "--workdir", type=Path, required=True, help="scratch directory for trial repos"
    )
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    args.workdir.mkdir(parents=True, exist_ok=True)
    for arm in args.arms:
        for i in range(args.trials):
            print(f"running {arm} trial {i + 1}/{args.trials}...", flush=True)
            record = trial(arm, i, args.workdir)
            (RESULTS / f"{arm}-{i}.json").write_text(json.dumps(record, indent=2))
            print(
                f"  tokens={record['tokens_total']} "
                f"repeated_failure={record['repeated_failure']} "
                f"correct={record['correct']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
