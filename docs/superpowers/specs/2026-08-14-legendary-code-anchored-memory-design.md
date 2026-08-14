# Legendary — Code-Anchored Memory for Coding Agents

**Date:** 2026-08-14
**Status:** Draft (pending user review)
**License target:** Open source (MIT)

## 1. Problem

Coding agents (Claude Code, Cursor, Codex, OpenHands) are stateless between
sessions and degrade within them:

- **Session amnesia:** each session re-reads the repo, re-derives decisions,
  and repeats debugging attempts that already failed. Rebuilding context costs
  an estimated 5–20k tokens per session (PROJECTMEM, arXiv:2606.12329).
- **Context rot:** output quality degrades at ~70–80% context fill; mid-context
  information is effectively ignored (Liu et al., "Lost in the Middle,"
  TACL 2024). Compaction is lossy and errors compound (arXiv:2608.01326).
- **Long-horizon collapse:** agents hit ~73% on single-issue SWE-bench Verified
  but ~25% on multi-iteration SWE-EVO (arXiv:2512.18470) — coherence and memory,
  not raw capability, are the bottleneck.
- **No principled memory policy:** existing memory stores have no notion of
  what to keep, when a memory goes stale, or how to surface it
  (arXiv:2606.24775; Red Hat, 2026).

### The gap

Existing tools sit on one side of a divide:

| Side | Tools | Blind spot |
|---|---|---|
| Code-structure | Serena, CodeGraph, GitNexus, cognee | Know *what* the code is; remember nothing about *why* or *what was tried* |
| Memory frameworks | Mem0, Zep/Graphiti, Letta | Remember conversations; code-blind — a memory doesn't know it's about `auth/session.py:42` and never invalidates when that code changes |

**Legendary merges the two:** memories anchored to code entities, with temporal
validity derived from git, stored in a git-native format.

## 2. Product definition

Legendary is a **local-first, open-source memory layer for coding agents**,
delivered as an MCP server + CLI. Its unit of value: a *memory* that is

1. **Anchored** — linked to a file/symbol/line-range at a specific commit.
2. **Typed** — `decision` | `episode` | `convention` | `reference`.
3. **Staleness-aware** — automatically flagged when the anchored code changes.
4. **Git-native** — stored as markdown in the repo, mergeable and reviewable
   like code (enables team sharing in a later phase with zero format change).

### Non-goals (v1)

- No cloud service, no telemetry, no accounts.
- No embeddings / vector DB / API keys (FTS5 + anchor matching only).
- No dashboard UI.
- No team sync mechanics (the storage format enables it; mechanics come later).
- No harness-specific integrations beyond Claude Code hooks (MCP tools already
  work in Cursor/Codex/any MCP client).

## 3. Architecture

```
┌─────────────────────────────────────────────────────┐
│ Coding agent (Claude Code / Cursor / any MCP host)  │
│   MCP tools: remember, recall, list_memories,       │
│              deprecate, stale_report                │
│   Hooks (Claude Code): SessionStart inject,         │
│                        SessionEnd extract           │
└──────────────────────┬──────────────────────────────┘
                       │
              legendary (Python 3.12, uv)
                       │
   ┌───────────────────┼──────────────────────┐
   │ core/             │                      │
   │  store.py   canonical markdown store     │
   │  index.py   derived SQLite FTS5 index    │
   │  anchor.py  file/symbol/hash anchoring   │
   │  stale.py   recall-time staleness check  │
   │  rank.py    recall ranking               │
   │  extract.py transcript → memory candidates│
   └───────────────────┬──────────────────────┘
                       │
        .legendary/            (in target repo)
          memories/*.md        committed, canonical
          index.db             gitignored, rebuildable
          config.toml          committed
```

### 3.1 Storage (`core/store.py`)

Canonical store: one markdown file per memory in `.legendary/memories/`,
frontmatter + body:

```markdown
---
id: mem-a1b2c3
type: episode            # decision | episode | convention | reference
title: Retry logic in sync worker breaks under SQLite WAL
created: 2026-08-14T15:30:00Z
source: agent            # agent | auto-extract | human
status: active           # active | deprecated
anchors:
  - file: src/sync/worker.py
    symbol: SyncWorker.run
    lines: [120, 164]
    commit: 8fa2c31
    content_hash: sha256:9f8e…   # hash of the anchored region at write time
tags: [sqlite, concurrency]
---
Tried wrapping retries in a transaction (attempt 1) — deadlocks under WAL
because …. Working approach: ….
```

Rationale: human-reviewable, PR-diffable, merge conflicts are legible, and a
teammate cloning the repo gets the memories for free.

Derived index: `index.db` (SQLite, FTS5 over title/body/tags + anchors table).
Always rebuildable from the markdown (`legendary reindex`). Gitignored.

### 3.2 Anchoring (`core/anchor.py`)

An anchor = `{file, symbol?, lines?, commit, content_hash}`.

- `content_hash` covers the anchored region (symbol body if symbol given, else
  line range, else whole file), normalized (whitespace-stripped) to avoid
  trivial invalidation.
- Symbol resolution v1: lightweight — tree-sitter for Python/TS/JS to map a
  symbol name to its current span. Fallback: line range, then whole file.
- Anchors are validated at write time (file must exist; symbol resolved if
  given).

### 3.3 Staleness (`core/stale.py`)

Computed **at recall time** — no daemon, no watchers:

1. Re-resolve the anchor against the working tree (symbol may have moved).
2. Rehash the region; compare with stored `content_hash`.
3. Result per anchor: `fresh` | `stale` (region changed) | `orphaned`
   (file/symbol gone).

Recall output includes staleness verdicts, e.g.
`⚠ stale — SyncWorker.run changed since 8fa2c31`. Stale memories are still
returned (the *why* often survives a refactor) but ranked lower and flagged so
the agent treats them skeptically. `stale_report` / `legendary doctor` lists
all stale/orphaned memories for cleanup.

### 3.4 Recall ranking (`core/rank.py`)

`score = w1·fts_relevance + w2·anchor_overlap + w3·recency − w4·staleness_penalty`

- `anchor_overlap`: boost memories anchored to files the caller passes as
  `files_in_focus` (the files the agent is currently editing).
- Weights in `config.toml`; sensible defaults; no ML in v1.
- Returns top-k (default 5) with staleness flags and anchor citations.

### 3.5 MCP server (`mcp/server.py`)

FastMCP (official `mcp` Python SDK). Tools:

| Tool | Signature (essentials) | Purpose |
|---|---|---|
| `remember` | type, title, body, anchors[], tags[] | Save a memory (validates + writes md + indexes) |
| `recall` | query, files_in_focus[], k | Ranked, staleness-flagged memories |
| `list_memories` | filter by type/tag/file | Browse |
| `deprecate` | id, reason | Soft-delete (status: deprecated, reason recorded) |
| `stale_report` | — | All stale/orphaned memories |

Run: `uvx legendary mcp` (stdio). One-line install in any MCP client.

### 3.6 CLI (`cli/`)

`legendary init` (scaffold .legendary/, gitignore index.db, print MCP/hook
setup) · `search` · `reindex` · `doctor` (stale report) · `extract <transcript>`.

### 3.7 Auto-capture hooks (Claude Code, v1 minimal)

- **SessionStart hook:** `legendary inject` — prints top-k memories relevant to
  the repo (recent + conventions) as additional context.
- **SessionEnd/Stop hook:** `legendary extract` — runs an LLM pass (via
  `claude -p` headless, so no separate API key) over the transcript to propose
  memories: decisions made, failures hit, conventions observed. Saved with
  `source: auto-extract` so humans/agents can audit or deprecate them.
- Hooks are optional; MCP tools alone are fully functional.

## 4. Error handling

- Not a git repo → clear error from `init`; staleness degrades gracefully
  (hash-only, no commit refs).
- Index corrupt/missing → auto-rebuild from markdown (canonical store wins).
- Anchor fails to resolve at write → reject with actionable message (agent can
  retry with a line range).
- Malformed memory file (hand-edited) → skipped with warning in `doctor`;
  never crashes recall.
- `claude -p` unavailable → `extract` exits with instructions; core unaffected.

## 5. Testing strategy

TDD throughout (pytest):

- **Unit:** store round-trip (md ↔ model), anchor resolution + normalization,
  hash stability, staleness verdicts (fresh/stale/orphaned via temp git repos),
  ranking order, extract prompt parsing.
- **Integration:** MCP tools end-to-end over a fixture repo (in-memory MCP
  client from the SDK); CLI via subprocess on temp repos.
- **Property-style:** reindex idempotence (reindex(reindex(x)) == reindex(x));
  markdown files survive round-trip without diff noise.

## 5b. Repo infrastructure (OSS hygiene)

- **MIT LICENSE** file.
- **CI (GitHub Actions):** on push/PR — `uv sync` + `pytest` on a matrix of
  {ubuntu, macos} × {3.12, 3.13}; `ruff check` for lint. Must pass before merge.
- **Release (GitHub Actions):** on version tag `v*` — build with `uv build`,
  publish to PyPI via trusted publishing (OIDC, no stored token). This is what
  makes `uvx legendary` work for end users.

## 6. Roadmap after v1

1. **v1.x** — extraction quality, more tree-sitter languages, Cursor/Codex hook
   equivalents.
2. **v2 (team)** — merge-friendly conventions, memory review workflow (PR
   template), per-branch memory visibility.
3. **v3** — optional local embeddings (e.g. sqlite-vec + small local model) for
  semantic recall; context-rot tooling (decision-preserving compaction notes).

## 7. Key risks

- **Agents don't call recall():** mitigated by SessionStart injection + a
  suggested CLAUDE.md snippet emitted by `init`.
- **Auto-extract noise:** mitigated by `source: auto-extract` provenance,
  deprecate flow, and conservative extraction prompt.
- **Symbol drift breaks anchors:** mitigated by re-resolution before hashing
  and graceful fallback to file-level anchoring.
