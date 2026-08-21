# Contributing to legendary

## Setup

```bash
git clone https://github.com/ashhadahsan/legendary
cd legendary
uv sync
uv run pytest -q
```

## Quality gates

Three checks, enforced in three places (pre-commit, CI, and a Claude Code hook):

```bash
uv run ruff format src tests   # formatting (black-compatible)
uv run ruff check src tests    # lint
uv run mypy                    # types
uv run pytest -q               # tests
```

Install the git hooks once:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

CI is the source of truth. A PR is not ready until `pre-commit run --all-files`
and `pytest` are both green on the matrix (ubuntu/macos x py3.12/3.13).

### Working on legendary with a coding agent

`scripts/quality_hook.py` is a Claude Code `PostToolUse` hook that formats,
lints, and type-checks each edited Python file and feeds failures straight back
to the agent. Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{"matcher": "Edit|Write",
      "hooks": [{"type": "command",
      "command": "uv run python scripts/quality_hook.py"}]}]
  }
}
```

## Module map

```
src/legendary/
  models.py       Anchor + Memory, markdown round-trip
  store.py        canonical markdown store (source of truth)
  anchor.py       symbol resolution (tree-sitter), normalization, hashing
  stale.py        recall-time fresh/stale/orphaned verdicts
  index.py        derived SQLite FTS5 index (disposable, auto-rebuilding)
  rank.py         weighted recall scoring
  service.py      shared application layer
  mcp_server.py   MCP tools (mcp 2.x SDK) - the optional add-on
  cli.py          CLI + both hooks (surface, guard) - the primary channel
```

## Ground rules

- **TDD.** Write the failing test first, watch it fail for the right reason,
  then implement.
- **The markdown store is canonical.** Any change must keep the markdown
  round-trip lossless; `index.db` must remain fully rebuildable from it.
- **Nothing calls an LLM.** v0.2 removed the last feature that did.
- **Hooks must never break the agent.** `surface` and `guard` exit 0 on any
  internal error, always.
- No AI-attribution trailers in commit messages.
