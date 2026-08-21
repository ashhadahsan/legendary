# Concepts

## Two delivery channels

Memory is only useful if it arrives when it is needed. legendary pushes on two
signals, and neither requires the agent to decide to ask.

**File-touch** (`surface`, PreToolUse) — the agent opens or edits a file, and
memories anchored to that file are injected.

**Error-signature** (`guard`, PostToolUse) — every episode stores the verbatim
error strings that produced it. When one of those strings appears in a Bash
result, the episode is pushed back.

The second channel exists because of how models use retrieved memory: an agent
acts on past experience when the current situation *resembles* the recorded
one. A recurring error message is the highest-fidelity resemblance signal a
coding agent ever produces — no query formulation, no embedding, no guesswork.

## Why episodes require triggers

An episode without a verbatim error string cannot be matched against a future
failure, so it can only be found by search — the weakest channel. legendary
rejects such writes with an actionable message rather than saving something
that will never resurface.

Good: `triggers: ["sqlite3.OperationalError: database is locked"]`
Useless: `triggers: ["database problem"]`

## Anchors and staleness

An anchor is `{file, symbol?, lines?, commit, content_hash}`. At write time the
symbol is resolved with tree-sitter and the region is hashed. At recall time it
is re-resolved and re-hashed.

| Verdict | Meaning |
|---|---|
| `fresh` | the region hashes the same — rendered `(verified against current code)` |
| `stale` | the region changed — rendered with an instruction to verify |
| `orphaned` | the file or symbol is gone |

Whitespace-only edits do not invalidate a memory, and a symbol that merely
moves stays fresh, because anchors re-resolve by symbol before hashing.

Staleness is what makes pushed procedure safe to act on. Delivering a confident
"do it this way" for code that has since changed is worse than delivering
nothing — it is the error-propagation failure mode that memory systems without
verification cannot avoid.

## Two memory types

| Type | For |
|---|---|
| `decision` | why the code is the way it is |
| `episode` | an approach that failed, and why (**requires triggers**) |

Conventions belong in CLAUDE.md and references in docs — both already have a
home with better delivery than any memory tool can offer. v0.2 removed those
types; memories written under them in v0.1 load as `decision`.

## Corrections cannot destroy knowledge

`supersedes` requires the replacing memory to cover every anchor of the memory
it replaces. This was added after observing a real agent deprecate a broad,
two-file memory with a narrower one, leaving a file with no active memory at
all. If you cannot cover the anchors, use `deprecate(reason=...)` instead.

## Storage

Markdown in `.legendary/memories/`, committed. `index.db` is a derived SQLite
FTS5 index — gitignored, versioned, and rebuilt automatically when missing,
corrupt, or written by an older schema.
