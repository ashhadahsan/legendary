"""legendary CLI: init | search | reindex | doctor | extract | inject | mcp."""

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
    "SessionStart": [{"hooks": [{"type": "command",
      "command": "uvx --from legendary-mcp legendary inject --repo %s"}]}],
    "SessionEnd": [{"hooks": [{"type": "command",
      "command": "uvx --from legendary-mcp legendary extract --repo %s"}]}]
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
    entry = ".legendary/index.db"
    existing = gitignore.read_text() if gitignore.exists() else ""
    if entry not in existing:
        gitignore.write_text(
            existing.rstrip("\n") + ("\n" if existing else "") + entry + "\n"
        )
    idx.rebuild(repo)
    print(f"initialized .legendary/ in {repo}\n")
    print(_MCP_SNIPPET % (repo, repo, repo))
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


def _cmd_extract(repo: Path, transcript: str | None) -> int:
    from legendary.extract import extract_from_transcript

    path = transcript
    if path is None:
        # Claude Code hooks pass JSON on stdin including transcript_path
        try:
            hook_input = json.load(sys.stdin)
            path = hook_input.get("transcript_path")
        except Exception:
            path = None
    if not path:
        print("error: no transcript (pass a path or pipe hook JSON)", file=sys.stderr)
        return 1
    try:
        saved = extract_from_transcript(repo, Path(path))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"extracted {len(saved)} memories: {', '.join(saved) if saved else '-'}")
    return 0


def _cmd_inject(repo: Path, k: int) -> int:
    """Print top memories for session-start context injection."""
    items = service.list_memories(repo)
    if not items:
        return 0
    items.sort(key=lambda m: m["created"], reverse=True)
    conventions = [m for m in items if m["type"] == "convention"][:k]
    recent = [m for m in items if m["type"] != "convention"][:k]
    from legendary.store import load

    print("# Legendary memories for this repo (use `recall` tool for more)\n")
    for m in conventions + recent:
        full = load(repo, m["id"])
        if full:
            print(f"- [{full.type}] {full.title}: {full.body[:200]}")
    return 0


def _cmd_mcp(repo: Path, transport: str, host: str, port: int) -> int:
    from legendary.mcp_server import run

    run(repo, transport=transport, host=host, port=port)
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
    p_extract = _add_repo(sub.add_parser("extract"))
    p_extract.add_argument("transcript", nargs="?", default=None)
    p_inject = _add_repo(sub.add_parser("inject"))
    p_inject.add_argument("-k", type=int, default=5)
    p_mcp = _add_repo(sub.add_parser("mcp"))
    p_mcp.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio (default) or stateless streamable HTTP",
    )
    p_mcp.add_argument("--host", default="127.0.0.1")
    p_mcp.add_argument("--port", type=int, default=8787)

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
        case "extract":
            return _cmd_extract(repo, args.transcript)
        case "inject":
            return _cmd_inject(repo, args.k)
        case "mcp":
            return _cmd_mcp(repo, args.transport, args.host, args.port)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
