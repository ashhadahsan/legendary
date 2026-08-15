# MCP tools

The server exposes five tools. Descriptions below are what the agent sees, so
they are written as instructions to the agent.

## `remember`

Save a memory anchored to code.

| Parameter | Type | Notes |
|---|---|---|
| `type` | str | `decision` / `episode` / `convention` / `reference` |
| `title` | str | short, searchable |
| `body` | str | the actual knowledge |
| `anchors` | list | `[{file, symbol?, lines?: [start, end]}]` |
| `tags` | list | optional |
| `supersedes` | str | id of a memory this one corrects |

`supersedes` deprecates the old memory and back-links it via `superseded_by`,
so corrections never destroy history.

## `recall`

Search memories. Pass the files you are editing as `files_in_focus` to boost
memories anchored to them. Every result carries a `staleness` flag.

```json
{"query": "wal deadlock", "files_in_focus": ["src/sync/worker.py"], "k": 5}
```

## `list_memories`

Browse without searching; filter by `type`, `tag`, or `file`.

## `deprecate`

Soft-delete a memory that is wrong, recording a `reason`. Deprecated memories
leave the search index but stay in git history.

## `stale_report`

Every active memory whose anchored code has changed or disappeared. Good for a
periodic cleanup pass.

## Suggested CLAUDE.md snippet

```markdown
Before editing a file, call the legendary `recall` tool with that file in
files_in_focus. When you make a decision, discover a convention, or an approach
fails, call `remember` and anchor it to the relevant file/symbol.
```
