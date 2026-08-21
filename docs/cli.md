# CLI

All commands take `--repo` (defaults to the current directory).

## `legendary init`

Scaffolds `.legendary/`, gitignores the index, and installs both hooks into
`.claude/settings.json`. Idempotent, and it merges rather than overwrites —
your existing hooks and settings are preserved.

## `legendary doctor`

Every memory whose anchored code changed or disappeared.

```console
$ legendary doctor
[stale] mem-a1b2c3d4: deferred BEGIN deadlocks
    stale: bump_counter (was 8fa2c31)
```

## `legendary search <query>`

Recall from the terminal, as JSON with staleness flags.

## `legendary surface`

The PreToolUse hook. Reads hook JSON on stdin, emits memories anchored to the
file being touched. Deduped per session.

## `legendary guard`

The PostToolUse hook. Reads hook JSON on stdin, and if a Bash result contains
any stored trigger string, emits the matching episodes. Deduped per session.

Both hooks exit 0 on any internal error — a broken hook must never break your
agent.

## `legendary reindex`

Rebuilds `index.db` from the markdown store. Rarely needed: recall
auto-rebuilds when the index is missing, corrupt, or from an older schema.

## `legendary mcp`

Runs the MCP server over stdio.
