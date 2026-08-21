#!/usr/bin/env python3
"""legendary benchmark v2: opaque-service scenario, reset between sessions.

Structural guarantees the v1 harness lacked:
- git hard-reset between sessions: memory is the ONLY cross-session channel
- the quirk lives in a harness-owned mock server, never in the trial repo
- dead ends are measured behaviorally from server logs, not text patterns
- each arm's configuration is asserted ACTIVE before a trial counts

KNOWN LIMITATION (measured, not assumed): CLAUDE_CONFIG_DIR isolation was
probed and rejected - it strips the operator's skills/plugins but also breaks
authentication (credentials live in the OS keychain). Trials therefore run with
the operator's global config present, exactly as v1 did. This affects all arms
equally, but it means results do not represent a stock agent. Each trial
records `operator_env` so the contamination is visible in the published data.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

BENCH = Path(__file__).parent
SCENARIO = BENCH / "scenario2"
RESULTS = BENCH / "results"

SESSION_1 = (
    "test_billing_reconciliation in tests/test_billing.py fails. Diagnose and "
    "fix billing/client.py so `pytest tests/test_billing.py` passes. The "
    "payments service URL is in the MOCKPAY_URL env var. Do not modify tests."
)
SESSION_2 = (
    "Implement billing/refunds.py so `pytest tests/test_refunds.py` passes. "
    "The payments service URL is in the MOCKPAY_URL env var. Do not modify "
    "tests."
)

ARMS = {
    "baseline": [],
    # the product's default install: hooks primary, MCP add-on
    "legendary": ["legendary", "hook"],
}

GIT_ID = ["-c", "user.email=b@b.b", "-c", "user.name=bench"]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_ID, *args], cwd=repo, check=True, capture_output=True)


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
    return {"mcpServers": servers}


def run_session(repo: Path, prompt: str, config_path: Path, mock_url: str) -> dict:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--max-turns",
        "40",
        "--mcp-config",
        str(config_path),
        "--strict-mcp-config",
    ]
    env = dict(os.environ, MOCKPAY_URL=mock_url)
    started = time.monotonic()
    proc = subprocess.run(
        cmd, cwd=repo, capture_output=True, text=True, timeout=1800, env=env
    )
    elapsed = time.monotonic() - started

    data = None
    init_tools: list[str] = []
    operator_env: dict = {}
    transcript: list[str] = []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            data = event
        elif event.get("type") == "system" and event.get("subtype") == "init":
            init_tools = event.get("tools", [])
            # measure the contamination we could not remove (see module docstring)
            operator_env = {
                "n_slash_commands": len(event.get("slash_commands", [])),
                "n_tools": len(init_tools),
            }
        elif event.get("type") == "assistant":
            transcript.append(json.dumps(event.get("message", {})))
    if data is None:
        return {
            "error": (proc.stdout[-2000:] or proc.stderr[-2000:]),
            "duration_s": round(elapsed, 1),
        }
    u = data.get("usage", {})
    text = "\n".join(transcript)
    return {
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "output_tokens": int(u.get("output_tokens", 0) or 0),
        "duration_s": round(elapsed, 1),
        "is_error": data.get("is_error"),
        "mcp_tools_offered": sorted(
            t for t in init_tools if t.startswith("mcp__legendary")
        ),
        "used_recall": "mcp__legendary__recall" in text,
        "used_remember": "mcp__legendary__remember" in text,
        "operator_env": operator_env,
        "transcript": text,
    }


def quirk_hits(log_path: Path, since_line: int) -> tuple[int, int]:
    """(#requests with dropped float amounts, new line count) since a marker."""
    if not log_path.exists():
        return 0, since_line
    lines = log_path.read_text().splitlines()
    hits = sum(
        1
        for line in lines[since_line:]
        if json.loads(line).get("n_dropped_float", 0) > 0
    )
    return hits, len(lines)


def tests_pass(repo: Path, mock_url: str, selector: str) -> bool:
    proc = subprocess.run(
        ["uv", "run", "--isolated", "--with", "pytest", "pytest", "-q", selector],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        env=dict(os.environ, MOCKPAY_URL=mock_url),
    )
    return proc.returncode == 0


def reset_repo(repo: Path, arm: str) -> None:
    """Session boundary: code reverts to broken; only memory artifacts survive."""
    git(repo, "reset", "--hard", "HEAD")
    keep = ["-e", ".claude", "-e", ".bench-mcp.json"]
    if "legendary" in ARMS[arm]:
        keep += ["-e", ".legendary"]
    subprocess.run(
        ["git", "clean", "-fdq", *keep], cwd=repo, check=True, capture_output=True
    )


def trial(arm: str, index: int, workdir: Path) -> dict:
    repo = workdir / f"{arm}-{index}"
    if repo.exists():
        shutil.rmtree(repo)
    shutil.copytree(SCENARIO, repo)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "scenario")

    tools = ARMS[arm]
    config_path = repo / ".bench-mcp.json"
    config_path.write_text(json.dumps(mcp_config(tools, repo)))
    if "legendary" in tools:
        # v0.2 init installs both hooks itself - that IS the product's default
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

    log_path = workdir / f"{arm}-{index}-mockpay.jsonl"
    port = free_port()
    mock_url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        ["python3", str(BENCH / "mockpay.py"), str(port), str(log_path)]
    )
    time.sleep(0.5)
    try:
        s1 = run_session(repo, SESSION_1, config_path, mock_url)
        s1_correct = tests_pass(repo, mock_url, "tests/test_billing.py")
        _, log_marker = quirk_hits(log_path, 0)

        wrote_memory = (
            bool(list((repo / ".legendary" / "memories").glob("*.md")))
            if "legendary" in tools
            else None
        )

        reset_repo(repo, arm)

        s2 = run_session(repo, SESSION_2, config_path, mock_url)
        s2_quirk_hits, _ = quirk_hits(log_path, log_marker)
        s2_correct = tests_pass(repo, mock_url, "tests/test_refunds.py")
        hook_fired = (
            bool(list((repo / ".legendary").glob(".surfaced-*")))
            if "hook" in tools
            else None
        )
    finally:
        server.terminate()

    # ---- arm-activation assertions: a trial that did not run its declared
    # configuration is classified, not silently averaged in ----
    activation_failures = []
    if "legendary" in tools:
        for s in (s1, s2):
            if "mcp__legendary__recall" not in s.get("mcp_tools_offered", []):
                activation_failures.append("mcp_tools_not_offered")
                break
        if wrote_memory is False:
            activation_failures.append("no_memory_written_in_s1")

    return {
        "arm": arm,
        "trial": index,
        "session_1": s1,
        "session_2": s2,
        "s1_correct": s1_correct,
        "s2_correct": s2_correct,
        "s2_quirk_hits": s2_quirk_hits,
        "wrote_memory": wrote_memory,
        "hook_fired": hook_fired,
        "activation_failures": activation_failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("-n", "--trials", type=int, default=10)
    ap.add_argument("--workdir", type=Path, required=True)
    args = ap.parse_args()

    # grep gate: the fixture must not contain quirk hints (pre-registered)
    leak = subprocess.run(
        ["grep", "-ri", "float", str(SCENARIO / "billing")], capture_output=True
    )
    if leak.returncode == 0:
        raise SystemExit(f"fixture leaks the quirk:\n{leak.stdout.decode()}")

    RESULTS.mkdir(exist_ok=True)
    args.workdir.mkdir(parents=True, exist_ok=True)
    for i in range(args.trials):
        for arm in args.arms:  # interleaved: interruption keeps arms balanced
            print(f"running {arm} trial {i + 1}/{args.trials}...", flush=True)
            record = trial(arm, i, args.workdir)
            for key in ("session_1", "session_2"):
                text = record[key].pop("transcript", "")
                (RESULTS / f"{arm}-{i}-{key}.txt").write_text(text)
            (RESULTS / f"{arm}-{i}.json").write_text(json.dumps(record, indent=2))
            print(
                f"  s2_quirk_hits={record['s2_quirk_hits']} "
                f"s2_correct={record['s2_correct']} "
                f"activation_failures={record['activation_failures']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
