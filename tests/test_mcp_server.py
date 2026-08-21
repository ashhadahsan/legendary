import asyncio
import json
from pathlib import Path

import pytest

from legendary.mcp_server import build_server


def call(server, name: str, args: dict):
    """Invoke a tool and return its parsed JSON payload."""
    result = asyncio.run(server.call_tool(name, args))
    assert result.is_error is False, result.content[0].text
    return json.loads(result.content[0].text)


def test_tool_schemas_expose_parameters(repo: Path):
    tools = {t.name: t for t in asyncio.run(build_server(repo).list_tools())}
    # mcp 2.x names this input_schema (1.x called it inputSchema)
    props = tools["recall"].input_schema["properties"]
    assert {"query", "files_in_focus", "k"} <= set(props)
    assert tools["recall"].description  # docstring becomes the agent-facing doc


def test_remember_then_recall_end_to_end(repo: Path):
    server = build_server(repo)
    saved = call(
        server,
        "remember",
        {
            "type": "episode",
            "title": "wal deadlock",
            "body": "busy_timeout fixes it",
            "anchors": [{"file": "src/sync/worker.py", "symbol": "SyncWorker.run"}],
            "tags": ["sqlite"],
            "triggers": ["database is locked"],
        },
    )
    assert saved["id"].startswith("mem-")
    payload = call(server, "recall", {"query": "wal deadlock"})
    assert payload[0]["title"] == "wal deadlock"
    assert payload[0]["staleness"] == "fresh"


def test_remember_bad_anchor_surfaces_error(repo: Path):
    server = build_server(repo)
    with pytest.raises(Exception, match="nope.py"):
        asyncio.run(
            server.call_tool(
                "remember",
                {
                    "type": "episode",
                    "title": "x",
                    "body": "y",
                    "anchors": [{"file": "nope.py"}],
                    "triggers": ["x"],
                },
            )
        )


def test_mcp_surface_is_exactly_three_tools(repo: Path):
    tools = asyncio.run(build_server(repo).list_tools())
    assert {t.name for t in tools} == {"remember", "recall", "deprecate"}
