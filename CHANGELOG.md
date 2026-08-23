# Changelog

All notable changes to legendary. Dates are the release date.

## [0.2.1] - 2026-08-21

### Fixed

- **`guard` could never match a trigger containing a quote, newline, tab or
  backslash.** The hook built its search text with `json.dumps()`, which
  escapes those characters, while comparing the stored trigger raw. Verified
  against real stored memories where 2 of 4 triggers were unmatchable despite
  appearing verbatim in the command output.
- **`remember` asked for triggers that could never recur.** It requested "the
  verbatim error strings or failing test names you observed", and agents
  complied — storing keys like `test_billing_reconciliation` that are
  guaranteed not to repeat. It now asks for the invariant part (exception type
  and message), and returns non-blocking `trigger_warnings` when a trigger
  looks occurrence-specific.

### Added

- `.legendary/.injections.jsonl` — both hooks record what they actually
  delivered. Hook output never appears in the agent transcript, so until now
  there was no way to answer "did the hook do anything".

## [0.2.0] - 2026-08-21

A breaking redesign. Push delivery became the primary channel and the memory
model shrank.

### Added

- **`guard` hook** (PostToolUse): episodes store verbatim error signatures and
  are pushed back when that failure reappears.
- `init` installs both hooks by default, merging into `.claude/settings.json`
  without disturbing existing configuration.
- Imperative rendering: `(verified against current code)` / `[stale - verify]`.

### Changed

- `supersedes` now requires the replacing memory to cover the old one's
  anchors, after a real agent was observed deprecating a broad memory with a
  narrow one and leaving a file uncovered.
- `files_in_focus` normalises absolute paths; hosts pass them, and v0.1
  silently lost the overlap boost.
- Ranking weights are fixed. The recency term was removed: a memory whose
  anchor still hashes fresh has survived, and staleness already measures drift.

### Removed (breaking)

- `extract` (LLM transcript pass) and `inject` (session-start dump).
- `convention` and `reference` memory types — memories using them load as
  `decision`.
- `list_memories` and `stale_report` MCP tools; `doctor` keeps stale reporting.
- Ranking config tunables and the HTTP transport.

## [0.1.1] - 2026-08-21

### Fixed

- **Recall silently lost memories to word-form drift.** FTS5 matched exact
  terms, so searching `deadlock` missed a memory saying "deadlocked". Now uses
  Porter stemming; the index schema is versioned and migrates automatically.
- Agent-facing recall payloads are 24% smaller — `content_hash` and internal
  scores are stripped, and a stale anchor reports `changed_since` instead.
- Writing a memory rebuilt the entire index (O(n) per write, O(n²) in bulk).
  Incremental upsert keeps writes flat at ~0.8 ms.

## [0.1.0] - 2026-08-21

Initial release: code-anchored memories with staleness detection, an MCP
server, a CLI, and SQLite FTS5 retrieval.
