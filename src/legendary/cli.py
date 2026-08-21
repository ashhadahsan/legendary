"""legendary CLI: init | search | reindex | doctor | surface | mcp."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from legendary import index as idx
from legendary import service

_CONFIG_TOML = """\
# legendary configuration
[rank]
# score = fts*w_fts + overlap*w_overlap + recency*w_recency - stale_penalty*w_stale
w_fts = 2.0
w_overlap = 1.5
w_recency = 0.5
w_stale = 1.0
"""

_MCP_SNIPPET = """\
Add legendary to your MCP client, e.g. Claude Code (.mcp.json):

{
  "mcpServers": {
    "legendary": {
      "command": "uvx",
      "args": ["--from", "legendary-mcp", "legendary", "mcp", "--repo", "%s"]
    }
  }
}

Claude Code hooks (.claude/settings.json) for auto-capture:

{
  "hooks": {
    "PreToolUse": [{"matcher": "Read|Edit|Write",
      "hooks": [{"type": "command",
      "command": "uvx --from legendary-mcp legendary surface --repo %s"}]}]
  }
}

Suggested CLAUDE.md snippet:
  Before editing a file, call the legendary `recall` tool with the file path
  in files_in_focus. After decisions or failed attempts, call `remember`.
"""


def _cmd_init(repo: Path) -> int:
    if not (repo / ".git").exists():
        print(
            f"error: {repo} is not a git repository (run `git init` first)",
            file=sys.stderr,
        )
        return 1
    (repo / ".legendary" / "memories").mkdir(parents=True, exist_ok=True)
    config = repo / ".legendary" / "config.toml"
    if not config.exists():
        config.write_text(_CONFIG_TOML)
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    additions = [
        e
        for e in (".legendary/index.db", ".legendary/.surfaced-*")
        if e not in existing
    ]
    if additions:
        gitignore.write_text(
            existing.rstrip("\n")
            + ("\n" if existing else "")
            + "\n".join(additions)
            + "\n"
        )
    idx.rebuild(repo)
    print(f"initialized .legendary/ in {repo}\n")
    print(_MCP_SNIPPET % (repo, repo))
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
        flag = (
            "" if verdict == "fresh" else f" [{verdict} - verify against current code]"
        )
        lines.append(f"- [{m.type}] {m.title}{flag}: {m.body[:300]}")
        rendered.append(mid)
    if not lines:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    # Only what was actually shown counts as seen, so a 6th memory on a hot
    # file still surfaces later instead of being suppressed forever.
    cache.write_text(" ".join(sorted(seen | set(rendered))))
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
        case "mcp":
            return _cmd_mcp(repo)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
