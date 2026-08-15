# CLI

All commands take `--repo` (defaults to the current directory).

## `legendary init`

Scaffolds `.legendary/`, writes `config.toml`, gitignores the index, and prints
MCP + hook configuration.

## `legendary search <query>`

Recall from the terminal. Outputs JSON including staleness flags.

```bash
legendary search "wal deadlock" -k 3
```

## `legendary doctor`

Lists every memory whose code changed or vanished.

```console
$ legendary doctor
[stale] mem-a1b2c3d4: Retry logic breaks under WAL
    stale: SyncWorker.run (was 8fa2c31)
```

## `legendary reindex`

Rebuilds `index.db` from the markdown store. Rarely needed - recall
auto-rebuilds when the index is missing or corrupt.

## `legendary inject`

Prints recent memories and conventions for session-start context injection.

## `legendary extract [transcript]`

Runs a headless `claude -p` pass over a session transcript and saves qualifying
memories with `source: auto-extract` and a `transcript` provenance ref. Reads
hook JSON from stdin when no path is given. This is the only feature that uses
an LLM; everything else is local and deterministic.

## `legendary surface`

The `PreToolUse` hook. Reads hook JSON on stdin and emits memories anchored to
the file being touched, deduplicated per session.

## `legendary mcp`

Runs the MCP server. Defaults to stdio.

```bash
legendary mcp --transport http --host 0.0.0.0 --port 8787
```

HTTP mode is **stateless** streamable HTTP: no per-session server state, so any
worker can serve any request. legendary is inherently stateless - the repo on
disk is the only state.
