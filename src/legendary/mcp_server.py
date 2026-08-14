"""MCP server exposing legendary's memory tools (mcp 2.x SDK)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

from legendary import service


def build_server(repo_root: Path) -> MCPServer:
    mcp = MCPServer(
        "legendary",
        instructions=(
            "Code-anchored memory for this repository. Call `recall` BEFORE "
            "starting work on a file to load prior decisions and failed "
            "attempts. Call `remember` when you make a decision, discover a "
            "convention, or an approach fails - anchor it to the relevant "
            "file/symbol. Memories flagged 'stale' refer to code that has "
            "changed since they were written: verify before trusting them."
        ),
    )

    @mcp.tool()
    def remember(
        type: str,
        title: str,
        body: str,
        anchors: Optional[list[dict]] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Save a memory. type: decision|episode|convention|reference.
        Each anchor: {file, symbol?, lines?: [start, end]}. Anchors are
        resolved and content-hashed now so staleness can be detected later."""
        return json.dumps(
            service.remember(
                repo_root,
                type=type,
                title=title,
                body=body,
                anchors=anchors,
                tags=tags,
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
        return json.dumps(service.recall(repo_root, query, files_in_focus, k))

    @mcp.tool()
    def list_memories(
        type: Optional[str] = None,
        tag: Optional[str] = None,
        file: Optional[str] = None,
    ) -> str:
        """Browse memories, optionally filtered by type, tag, or anchored file."""
        return json.dumps(
            service.list_memories(repo_root, type=type, tag=tag, file=file)
        )

    @mcp.tool()
    def deprecate(memory_id: str, reason: str) -> str:
        """Soft-delete a memory that is wrong or superseded. Records the reason."""
        return json.dumps(service.deprecate(repo_root, memory_id, reason))

    @mcp.tool()
    def stale_report() -> str:
        """List all memories whose anchored code has changed or disappeared."""
        return json.dumps(service.stale_report(repo_root))

    return mcp


def run(
    repo_root: Path,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8787,
) -> None:
    """Serve over stdio (default) or stateless streamable HTTP.

    Stateless HTTP holds no per-session server state, so any number of workers
    can serve any request - the right shape for containers and shared team
    deployments. legendary itself is already stateless: the repo on disk is the
    only state.
    """
    server = build_server(repo_root)
    if transport == "stdio":
        server.run()
        return
    import anyio

    anyio.run(
        lambda: server.run_streamable_http_async(
            host=host, port=port, stateless_http=True, json_response=True
        )
    )
