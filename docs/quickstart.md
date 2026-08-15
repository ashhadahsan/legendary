# Quickstart

## Install and initialize

```bash
cd your-repo
uvx --from legendary-mcp legendary init
```

This creates `.legendary/`, gitignores the derived index, and prints the MCP
and hook configuration to paste into your agent.

## Connect your agent

Add the printed snippet to your MCP client. For Claude Code, `.mcp.json`:

```json
{
  "mcpServers": {
    "legendary": {
      "command": "uvx",
      "args": ["--from", "legendary-mcp", "legendary", "mcp", "--repo", "/path/to/your-repo"]
    }
  }
}
```

## See staleness work (the 2-minute "aha")

Save a memory anchored to a function:

```python
from pathlib import Path
from legendary import service

service.remember(
    repo_root=Path("."),
    type="episode",
    title="strip() crashes on None",
    body="Tried data.strip() directly - crashes when data is None. Guard first.",
    anchors=[{"file": "app.py", "symbol": "parse"}],
)
```

Recall it - it is `fresh`:

```bash
legendary search "strip None"
```

Now edit `parse` in `app.py` and recall again. The same memory comes back
flagged `stale`, because the hash of the anchored region no longer matches.

## Automatic surfacing (recommended)

The biggest failure mode of agent memory is that agents forget to *ask* for it.
The `PreToolUse` hook removes that problem: whenever the agent reads or edits a
file, memories anchored to it are injected automatically.

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Read|Edit|Write",
      "hooks": [{"type": "command",
      "command": "uvx --from legendary-mcp legendary surface --repo /path/to/your-repo"}]}]
  }
}
```

Memories are deduplicated per session, so you see each one once.
