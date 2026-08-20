# Legendary v2 — From Memory Database to Delivery-and-Verification Layer

**Date:** 2026-08-20
**Status:** Approved (full adoption of the independent design brief)
**Basis:** Adversarial design review (Fable) grounded in: the retracted n=5 benchmark
and its four confounds, the hook-arm transcripts, trial-repo forensics, and four
verified papers (arXiv 2603.02473; ACL 2026.acl-long.27; Memp 2508.06433;
CODESKILL 2605.25430).

## 1. The verdict on v1

The premise "coding agents need a parallel memory database with its own search
engine" is **not sound**:

- Comments/ADRs are code-anchored memories with perfect anchoring and free
  delivery; CLAUDE.md is host-injected convention memory. Three of v1's four
  memory types duplicate artifacts that already have a home.
- Retrieval research: retrieval method moves accuracy ~20 points; write-side
  sophistication moves 3–8, and raw content matches curated extraction.
- Measured overhead of v1 on tasks that don't need memory: +30–80% cost.

What has **no** home elsewhere, and survives as the product:

1. **Negative knowledge** — approaches tried and reverted, runtime-discovered
   constraints. Nobody writes comments on code that doesn't exist.
2. **Verification** — staleness (hash-compare against current code) is the only
   mechanism in the field that validates a natural-language claim. It survives
   untouched at the center.
3. **Push delivery** — the hook transcripts are direct evidence: file-keyed
   just-in-time injection steered 2/2 agents to a one-edit fix, explicitly
   citing the memory.

**v2 is a delivery-and-verification layer, not a database.** ~600 lines, down
from ~1,310.

## 2. Architecture inversion

- `legendary init` installs the **hooks by default** (merging into the target
  repo's `.claude/settings.json`, idempotently): PreToolUse (Read|Edit|Write →
  `surface`) and PostToolUse (Bash → `guard`). The MCP server becomes the
  optional add-on.
- **New trigger channel:** memories carry `triggers` — verbatim error strings /
  failing test names captured at write time. `legendary guard` (PostToolUse on
  Bash) scans tool output for stored triggers and injects the matching episode.
  This is experience-following made mechanical: a recurring error message is
  the highest-fidelity input-similarity signal an agent emits, and requires no
  query formulation.
- **Imperative payloads:** surfaced memories render as guardrails.
  Fresh → `(verified against current code)` — licenses acting without
  re-derivation. Stale → `[stale - code changed since <commit>; verify]`.
- **Write-time discipline:** an `episode` without `triggers` is rejected with
  an actionable message. The resemblance hooks must exist for
  experience-following to fire.

## 3. Memory model

- Types: **`decision` | `episode` only.** `convention`/`reference` deleted
  (CLAUDE.md's and docs' job). Legacy stored memories with removed types are
  coerced to `decision` at load (no data loss).
- New field: `triggers: list[str]` (indexed; required for episodes).
- `supersedes` **requires anchor coverage**: the new memory's anchor files must
  be a superset of the old one's, else the call is rejected — fixes the
  observed knowledge-destruction failure (trial repo forensics: a two-anchor
  general memory was deprecated by a narrower one, leaving a file uncovered).

## 4. Retrieval / ranking

- Fixed weights: `fts + focus_overlap − staleness`. The `[rank]` config
  tunables and **recency term are deleted** — an old memory whose anchor still
  hashes fresh *survived*; recency double-penalizes durability, and staleness
  already measures drift.
- `files_in_focus` is normalized (absolute → repo-relative) before overlap
  matching; hosts pass absolute paths and v1 silently got zero boost.

## 5. Cuts (deleted outright in v0.2.0 — breaking release)

| Cut | Reason |
|---|---|
| `extract` (SessionEnd LLM auto-extraction) | Write-side sophistication worth 3–8 pts vs retrieval's 20; costs a `claude -p` per session; its fallback silently strips anchors, manufacturing unverifiable memories with `auto-extract` provenance |
| `inject` (SessionStart dump) | Wrong timing; never referenced in any transcript; CLAUDE.md's job |
| `convention`, `reference` types | Duplicate CLAUDE.md/docs with worse delivery |
| `stale_report` MCP tool | Maintenance op; never called by any agent; demoted to CLI `doctor` |
| `[rank]` tunables + recency | See §4 |
| HTTP transport | Speculative infra, zero demonstrated users; stdio + git-native sharing suffice |

Agent-facing MCP surface: exactly `recall`, `remember`, `deprecate`.

## 6. Benchmark v2 — structurally ungameable

- **Hard reset between sessions:** after session 1, `git reset --hard` +
  `git clean` (preserving only the arm's memory/config artifacts). Memory is
  the only channel by construction; also exercises staleness honestly.
- **Opaque-service fixture:** a harness-owned HTTP mock (never inside the trial
  repo) with a realistic quirk — records whose `amount` is a JSON float are
  silently dropped while returning 200 accepted. Session 1: fix billing
  reconciliation (only discoverable by experiment). Session 2 (post-reset):
  implement refunds against a second endpoint with the same quirk.
- **Behavioral dead-end metric:** the server logs every request;
  `quirk_hits_s2` counts session-2 requests containing float amounts. Textually
  unrelated to anything in the repo. A grep gate asserts no dead-end-adjacent
  strings exist in the fixture before any trial counts.
- **Arm-activation assertions** before a trial counts: expected MCP tools in
  the init event; `.surfaced-*` cache exists for hook arms (canary memory
  pre-seeded); ≥1 agent-written memory after session 1 (else classified
  `no_write`, reported separately).
- **Isolated agent environment:** `CLAUDE_CONFIG_DIR` pointed at a minimal
  isolated dir so operator skills/plugins cannot leak (confound F3).
- **Endpoints:** session-2 `quirk_hits`, session-2 cost/turns-to-green
  (session 1 reported separately — summing buries the effect under write-time
  overhead). n ≥ 10/arm, interleaved, medians + ranges. "Delivered-and-ignored"
  is decided by ordering: injection timestamp vs first quirk hit.
- The 2026-08-15 fixture is **retired**; re-running it reproduces retracted
  defects at real cost.

## 7. Error handling

- `guard`/`surface` are hooks: any internal failure exits 0 silently (a broken
  hook must never break the agent).
- Legacy-type coercion happens in the model validator, so every load path
  (store, index rebuild, recall) benefits.
- Supersede-coverage rejection and episode-trigger rejection return actionable
  ValueErrors through the existing MCP error path (agents retry well — observed
  in trials).

## 8. Testing strategy

TDD per task, as v1. Deletions update counts explicitly. New behavior gets
regression tests: legacy coercion, trigger enforcement, coverage-gated
supersede, path normalization, guard matching + dedupe, imperative rendering,
schema v3 migration. Fixture validated: broken fails; string-decimal fix
passes; retries/timeouts don't help.

## 9. Out of scope (v2.x)

`disputed` outcome-feedback loop (needs a reliable "fix contradicts memory"
detector); import-graph reranking; per-module digests; Graphify benchmark arm.
