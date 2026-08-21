# Quickstart

## Install

```bash
cd your-repo
uvx --from legendary-mcp legendary init
```

That creates `.legendary/`, gitignores the derived index, and **installs both
hooks** into `.claude/settings.json` — merging into your existing settings
without touching anything else you have configured there.

You are done. The hooks are the primary channel and need no agent cooperation.

## Optional: agent-initiated search

`init` also prints an MCP snippet. Add it to `.mcp.json` if you want the agent
to be able to search memory deliberately, on top of what gets pushed:

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

Three tools: `remember`, `recall`, `deprecate`.

## Record your first episode

Episodes are the point of the tool, and they **require triggers** — the
verbatim error strings you observed:

```python
from pathlib import Path
from legendary import service

service.remember(
    repo_root=Path("."),
    type="episode",
    title="strip() crashes on None",
    body="Use a guard: data.strip() if data else ''. Retries do not help.",
    anchors=[{"file": "app.py", "symbol": "parse"}],
    triggers=["AttributeError: 'NoneType' object has no attribute 'strip'"],
)
```

Now the next time any command prints that error, the episode is pushed back
automatically. Without the trigger there is nothing to match on, which is why
legendary refuses to save an episode that omits it.

## See verification work

Edit the anchored function, then trigger the error again. The same memory
returns marked `[stale - code changed since this was written; verify before
trusting]`.

Run `legendary doctor` any time for every memory whose code has moved on.
