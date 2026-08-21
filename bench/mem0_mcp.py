#!/usr/bin/env python3
"""Minimal MCP adapter exposing mem0 as a benchmark arm.

FAIRNESS NOTE - read this before trusting any mem0-vs-legendary number.

This adapter is ours, not mem0's. It is deliberately thin: two tools that map
directly onto mem0's own documented API (`Memory.add` and `Memory.search`),
with no filtering, reranking, or prompt engineering of our own on either side.
mem0 does its own fact extraction and semantic retrieval exactly as designed.

It is published so anyone can audit whether the comparison was fair. If you
believe a different mem0 configuration would perform better, the config is one
constructor call below - change it and re-run.

Requires an LLM + embedder, per mem0's architecture. Either provider works:
  OPENAI_API_KEY   - mem0's own default for both
  GEMINI_API_KEY   - equivalent, and has a free tier
Storage is embedded Qdrant on local disk (mem0's default), so no server needed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer


def build_server(repo_root: Path) -> MCPServer:
    from mem0 import Memory

    # mem0's stock configuration except for two things: the storage path is
    # pinned so trials do not leak memories into each other, and the provider
    # follows whichever key is present. Nothing about retrieval is altered.
    config: dict = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "bench",
                "path": str(repo_root / ".mem0" / "qdrant"),
                "on_disk": True,
            },
        },
        "history_db_path": str(repo_root / ".mem0" / "history.db"),
    }
    if not os.environ.get("OPENAI_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        config["llm"] = {"provider": "gemini", "config": {}}
        config["embedder"] = {"provider": "gemini", "config": {}}
        # gemini embeddings are 768-dim; qdrant must be told, or writes fail
        config["vector_store"]["config"]["embedding_model_dims"] = 768
    memory = Memory.from_config(config)
    user_id = "bench"

    mcp = MCPServer(
        "mem0",
        instructions=(
            "Long-term memory. `add_memory` to store what you learn; "
            "`search_memory` before starting work to recall it."
        ),
    )

    @mcp.tool()
    def add_memory(text: str) -> str:
        """Store a durable fact, decision, or lesson learned for future sessions."""
        result = memory.add(text, user_id=user_id)
        return json.dumps(result, default=str)

    @mcp.tool()
    def search_memory(query: str, limit: int = 5) -> str:
        """Search stored memories relevant to the current task."""
        result = memory.search(query, user_id=user_id, limit=limit)
        return json.dumps(result, default=str)

    return mcp


def main() -> int:
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        raise SystemExit(
            "mem0 arm requires OPENAI_API_KEY or GEMINI_API_KEY (mem0 needs an "
            "LLM for fact extraction and an embedder for retrieval). legendary "
            "requires neither; see docs/comparison.md."
        )
    import sys

    repo_root = Path(sys.argv[sys.argv.index("--repo") + 1])
    build_server(repo_root).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
