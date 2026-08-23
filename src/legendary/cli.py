"""legendary CLI: init | search | reindex | doctor | surface | guard | mcp."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from legendary import index as idx
from legendary import service

_MCP_SNIPPET = """\
Hooks installed in .claude/settings.json (primary channel - memories arrive
automatically). Optional add-on, agent-initiated search via MCP (.mcp.json):

{
  "mcpServers": {
    "legendary": {
      "command": "uvx",
      "args": ["--from", "legendary-mcp", "legendary", "mcp", "--repo", "%s"]
    }
  }
}

Suggested CLAUDE.md line:
  When an approach fails, call the legendary `remember` tool with type=episode
  and the verbatim error string as a trigger.
"""


def _install_hooks(repo: Path) -> None:
    """Merge legendary's hooks into .claude/settings.json, idempotently.

    Never clobbers user configuration: unknown keys and existing hook entries
    are preserved; our entries are recognized by their command substring."""
    settings_path = repo / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError):
        settings = {}
    hooks = settings.setdefault("hooks", {})
    wanted = {
        "PreToolUse": (
            "Read|Edit|Write",
            f"uvx --from legendary-mcp legendary surface --repo {repo}",
        ),
        "PostToolUse": (
            "Bash",
            f"uvx --from legendary-mcp legendary guard --repo {repo}",
        ),
    }
    for event, (matcher, command) in wanted.items():
        entries = hooks.setdefault(event, [])
        marker = command.split(" --repo ")[0]
        if not any(
            marker in h.get("command", "") for e in entries for h in e.get("hooks", [])
        ):
            entries.append(
                {
                    "matcher": matcher,
                    "hooks": [{"type": "command", "command": command}],
                }
            )
    settings_path.parent.mkdir(exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _cmd_init(repo: Path) -> int:
    if not (repo / ".git").exists():
        print(
            f"error: {repo} is not a git repository (run `git init` first)",
            file=sys.stderr,
        )
        return 1
    (repo / ".legendary" / "memories").mkdir(parents=True, exist_ok=True)
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    additions = [
        e
        for e in (
            ".legendary/index.db",
            ".legendary/.surfaced-*",
            ".legendary/.guarded-*",
            ".legendary/.injections.jsonl",
        )
        if e not in existing
    ]
    if additions:
        gitignore.write_text(
            existing.rstrip("\n")
            + ("\n" if existing else "")
            + "\n".join(additions)
            + "\n"
        )
    _install_hooks(repo)
    idx.rebuild(repo)
    print(f"initialized .legendary/ in {repo}\n")
    print(_MCP_SNIPPET % repo)
    return 0


def _cmd_search(repo: Path, query: str, k: int) -> int:
    print(json.dumps(service.recall(repo, query, k=k), indent=2))
    return 0


def _cmd_reindex(repo: Path) -> int:
    n = idx.rebuild(repo)
    print(f"indexed {n} memories")
    return 0


def _cmd_doctor(repo: Path) -> int:
    report = service.stale_report(repo)
    if not report:
        print("all memories fresh")
        return 0
    for item in report:
        print(f"[{item['staleness']}] {item['id']}: {item['title']}")
        for a in item["anchors"]:
            if a["staleness"] != "fresh":
                where = a.get("symbol") or a["file"]
                print(f"    {a['staleness']}: {where} (was {a.get('commit', '?')})")
    return 0


def _audit(
    repo: Path, hook: str, session: str, memory_ids: list[str], **extra: object
) -> None:
    """Append one record of what a hook actually delivered.

    Without this there is no way - for a user or for us - to answer "did the
    hook do anything?". Hook output does not appear in the agent transcript,
    and the dedupe caches record only that something happened, never what or
    when. Never raises: a broken hook must not break the agent.
    """
    try:
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "hook": hook,
            "session_id": session,
            "memory_ids": memory_ids,
            **extra,
        }
        path = repo / ".legendary" / ".injections.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    except Exception:
        pass


def _change_size(repo: Path, commit: str, file: str) -> str:
    """`+18 -4` for the anchored file since the commit it was verified at.

    Included so the agent can judge whether the change is worth reading before
    spending a turn on `git diff`. Never raises: a broken hook must not break
    the agent, and a missing commit just means no summary.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--numstat", f"{commit}..HEAD", "--", file],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return ""
        added, removed, *_ = out.stdout.split()
        return f" (+{added} -{removed})"
    except Exception:
        return ""


def _render_memory(m: object, verdict: str, repo: Path | None = None) -> str:
    """Imperative guardrail rendering shared by surface and guard.

    Fresh licenses acting without re-derivation. Stale must be *actionable*:
    saying "the code changed" without saying which file, which commit, or how
    to see the change leaves the reader to go find it themselves.
    """
    title = getattr(m, "title")
    body = getattr(m, "body")[:300]
    mtype = getattr(m, "type")
    created = getattr(m, "created", None)
    when = created.date().isoformat() if created else "unknown date"

    anchors = getattr(m, "anchors", []) or []
    anchor = anchors[0] if anchors else None
    where = getattr(anchor, "file", None) if anchor else None
    commit = getattr(anchor, "commit", None) if anchor else None

    if verdict == "fresh":
        scope = f"{where} @ {commit}" if where and commit else "current code"
        return (
            f"- [{mtype}] {title} (recorded {when}, verified against {scope}): {body}"
        )

    if where and commit:
        size = _change_size(repo, commit, where) if repo else ""
        detail = (
            f"{verdict} - {where} changed since {commit}{size}, recorded {when}; "
            f"see: git diff {commit}..HEAD -- {where}"
        )
    else:
        detail = f"{verdict} - recorded {when}; the anchored code has changed, verify"
    return f"- [{mtype}] {title} [{detail}]: {body}"


def _cmd_surface(repo: Path) -> int:
    """PreToolUse hook: surface memories anchored to the file being touched."""
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return 0  # not hook-invoked; stay silent
    tool_input = hook.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0
    try:
        rel = str(Path(file_path).resolve().relative_to(repo))
    except ValueError:
        return 0  # file outside this repo
    from legendary.index import memories_for_file

    ids = memories_for_file(repo, rel)
    if not ids:
        return 0
    session = hook.get("session_id") or "default"
    cache = repo / ".legendary" / f".surfaced-{session}"
    seen = set(cache.read_text().split()) if cache.exists() else set()
    new_ids = [i for i in ids if i not in seen]
    if not new_ids:
        return 0
    from legendary.stale import check_memory, worst_verdict
    from legendary.store import load

    lines = []
    rendered: list[str] = []
    for mid in new_ids[:5]:
        m = load(repo, mid)
        if m is None or m.status != "active":
            continue
        verdict = worst_verdict(check_memory(repo, m.anchors))
        lines.append(_render_memory(m, verdict, repo))
        rendered.append(mid)
    if not lines:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    # Only what was actually shown counts as seen, so a 6th memory on a hot
    # file still surfaces later instead of being suppressed forever.
    cache.write_text(" ".join(sorted(seen | set(rendered))))
    _audit(repo, "surface", session, rendered, file=rel)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"Legendary memories anchored to {rel}:\n" + "\n".join(lines)
                    ),
                }
            }
        )
    )
    return 0


def _haystack(obj: object) -> str:
    """Flatten a tool response to the raw text it actually emitted.

    Deliberately NOT json.dumps: that escapes quotes, newlines and backslashes,
    so any trigger containing one could never match output that verbatim
    contained it. Agents naturally write triggers like
    `server_totals()["batch"]`, and every one of them was dead.
    """
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


def _cmd_guard(repo: Path) -> int:
    """PostToolUse hook on Bash: inject episodes whose triggers match output.

    A recurring error string is the highest-fidelity experience-following
    signal an agent emits - no query formulation needed. Any internal failure
    exits 0: a broken hook must never break the agent.
    """
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return 0
    if hook.get("tool_name") != "Bash":
        return 0
    haystack = _haystack(hook.get("tool_response") or {})
    if not haystack or haystack == "{}":
        return 0
    from legendary.index import all_triggers

    matched = [
        (mid, trig) for mid, trig in all_triggers(repo) if trig.lower() in haystack
    ]
    matched_ids = {mid for mid, _ in matched}
    if not matched_ids:
        return 0
    session = hook.get("session_id") or "default"
    # separate cache from `surface`: sharing one file made the two channels
    # indistinguishable when analysing which one delivered value
    cache = repo / ".legendary" / f".guarded-{session}"
    seen = set(cache.read_text().split()) if cache.exists() else set()
    new_ids = sorted(matched_ids - seen)
    if not new_ids:
        return 0
    from legendary.stale import check_memory, worst_verdict
    from legendary.store import load

    lines = []
    rendered: list[str] = []
    for mid in new_ids[:3]:
        m = load(repo, mid)
        if m is None or m.status != "active":
            continue
        verdict = worst_verdict(check_memory(repo, m.anchors))
        lines.append(_render_memory(m, verdict, repo))
        rendered.append(mid)
    if not lines:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(" ".join(sorted(seen | set(rendered))))
    _audit(
        repo,
        "guard",
        session,
        rendered,
        triggers=[trig for mid, trig in matched if mid in rendered],
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "This failure has been seen before. Recorded episodes:\n"
                        + "\n".join(lines)
                    ),
                }
            }
        )
    )
    return 0


def _cmd_mcp(repo: Path) -> int:
    from legendary.mcp_server import run

    run(repo)
    return 0


def _add_repo(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """--repo must live on EVERY subparser, not the main parser.

    argparse gives trailing options to the subparser, so `legendary init --repo X`
    fails with 'unrecognized arguments' if --repo is only on the main parser.
    """
    p.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="target repository root (default: cwd)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="legendary")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_repo(sub.add_parser("init"))
    p_search = _add_repo(sub.add_parser("search"))
    p_search.add_argument("query")
    p_search.add_argument("-k", type=int, default=5)
    _add_repo(sub.add_parser("reindex"))
    _add_repo(sub.add_parser("doctor"))
    _add_repo(sub.add_parser("surface"))
    _add_repo(sub.add_parser("guard"))
    _add_repo(sub.add_parser("mcp"))

    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    match args.command:
        case "init":
            return _cmd_init(repo)
        case "search":
            return _cmd_search(repo, args.query, args.k)
        case "reindex":
            return _cmd_reindex(repo)
        case "doctor":
            return _cmd_doctor(repo)
        case "surface":
            return _cmd_surface(repo)
        case "guard":
            return _cmd_guard(repo)
        case "mcp":
            return _cmd_mcp(repo)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
