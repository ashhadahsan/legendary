# MCP tools

Three tools. The hooks are the primary channel; these exist for deliberate,
agent-initiated search.

## `remember`

| Parameter | Type | Notes |
|---|---|---|
| `type` | str | `decision` or `episode` |
| `title` | str | short, searchable |
| `body` | str | write it as an instruction, not a description |
| `anchors` | list | `[{file, symbol?, lines?: [start, end]}]` |
| `tags` | list | optional |
| `triggers` | list | **required for episodes** — verbatim error strings |
| `supersedes` | str | id of a memory this corrects (must cover its anchors) |

```json
{
  "type": "episode",
  "title": "deferred BEGIN deadlocks under concurrency",
  "body": "Use BEGIN IMMEDIATE. busy_timeout cannot fix a write-write conflict - SQLite raises SQLITE_BUSY on lock upgrade without calling the busy handler.",
  "anchors": [{"file": "sync/worker.py", "symbol": "bump_counter"}],
  "triggers": ["sqlite3.OperationalError: database is locked"]
}
```

Write bodies as guardrails: *"Use X, not Y, because Z"* — with the causal
clause, so a future reader can judge whether the reason still applies instead
of cargo-culting the fix.

## `recall`

Search. Pass the files you are editing as `files_in_focus` (absolute or
relative — both work) to boost memories anchored to them. Every result carries
a `staleness` flag.

## `deprecate`

Soft-delete a memory that is wrong, recording a reason. It leaves the search
index but stays in git history.

## Suggested CLAUDE.md line

```markdown
When an approach fails, call the legendary `remember` tool with type=episode
and the verbatim error string as a trigger.
```
