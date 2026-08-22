"""MCP server exposing legendary's memory tools (mcp 2.x SDK)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

from legendary import service


def _slim(results: list[dict]) -> list[dict]:
    """Strip internal bookkeeping before sending results to an agent.

    `content_hash` (64-char sha256) and `score` are implementation detail the
    agent cannot act on, but they are re-sent on every turn the result stays in
    context. `commit` is kept only when it is actionable - i.e. when the anchor
    is no longer fresh, so the agent can diff against it.
    """
    slim = []
    for r in results:
        anchors = []
        for a in r.get("anchors", []):
            keep = {k: v for k, v in a.items() if k not in ("content_hash", "commit")}
            if a.get("staleness") != "fresh" and a.get("commit"):
                keep["changed_since"] = a["commit"]
            anchors.append(keep)
        slim.append({k: v for k, v in r.items() if k != "score"} | {"anchors": anchors})
    return slim


def build_server(repo_root: Path) -> MCPServer:
    mcp = MCPServer(
        "legendary",
        instructions=(
            "Repo memory. `recall` before editing a file; `remember` decisions "
            "and failed attempts, anchored to file/symbol. 'stale' means the "
            "anchored code changed since - verify before trusting."
        ),
    )

    @mcp.tool()
    def remember(
        type: str,
        title: str,
        body: str,
        anchors: Optional[list[dict]] = None,
        tags: Optional[list[str]] = None,
        supersedes: Optional[str] = None,
        triggers: Optional[list[str]] = None,
    ) -> str:
        """Save a memory. type: decision|episode.
        Each anchor: {file, symbol?, lines?: [start, end]}. Anchors are
        resolved and content-hashed now so staleness can be detected later.
        Pass supersedes=<memory_id> when this memory corrects an existing one:
        the old memory is deprecated and back-linked instead of being lost.
        type=episode REQUIRES triggers: the part of the failure that will be
        byte-identical next time - the exception type and message, e.g.
        "sqlite3.OperationalError: database is locked". NOT test names and NOT
        specific numbers; those change between occurrences, so a memory keyed on
        them never fires again."""
        return json.dumps(
            service.remember(
                repo_root,
                type=type,
                title=title,
                body=body,
                anchors=anchors,
                tags=tags,
                supersedes=supersedes,
                triggers=triggers,
            )
        )

    @mcp.tool()
    def recall(
        query: str,
        files_in_focus: Optional[list[str]] = None,
        k: int = 5,
    ) -> str:
        """Search memories. Pass the files you are editing as files_in_focus
        to boost memories anchored to them. Results include a staleness flag
        per memory: fresh | stale (code changed) | orphaned (code gone)."""
        return json.dumps(_slim(service.recall(repo_root, query, files_in_focus, k)))

    @mcp.tool()
    def deprecate(memory_id: str, reason: str) -> str:
        """Soft-delete a memory that is wrong or superseded. Records the reason."""
        return json.dumps(service.deprecate(repo_root, memory_id, reason))

    return mcp


def run(repo_root: Path) -> None:
    """Serve the MCP tools over stdio."""
    build_server(repo_root).run()
