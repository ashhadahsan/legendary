# Benchmark

legendary ships a reproducible, four-arm benchmark rather than asking you to
take a claim on trust. The methodology is **pre-registered and committed**
before any run, so results cannot be retro-fitted to a conclusion.

## What it measures

Two sessions with separate context - the amnesia boundary is the thing under
test:

1. **Session 1** fixes a concurrency bug in `sync/worker.py`. The plausible fix
   (wrapping writes in `BEGIN TRANSACTION`) does *not* work; the working fix is
   `PRAGMA busy_timeout`. The agent learns this the hard way.
2. **Session 2**, with fresh context, fixes the same class of bug in
   `sync/reporter.py`. An agent with no memory of session 1 tends to retry the
   approach that already failed.

The fixture is validated three ways: broken -> both tests fail;
`busy_timeout` -> both pass; `BEGIN TRANSACTION` -> still fails.

## Arms

| Arm | Configuration |
|---|---|
| `baseline` | no memory, no graph tooling |
| `graphify` | Graphify MCP only |
| `legendary` | legendary MCP only |
| `both` | Graphify + legendary |

Graphify is included because it is the nearest well-known tool, and because the
honest hypothesis is that the two are **complementary**: Graphify models code
structure, legendary remembers decisions and failures. If `both` wins, that is
what gets published.

## Metrics

- `tokens_total` - input + cache + output across both sessions
- `cost_usd`, `duration_s`, `num_turns`
- `repeated_failure` - did session 2 reintroduce the known-bad pattern?
  Detected deterministically from the diff, not by an LLM judge.
- `correct` - does the test suite pass at the end?

## Running it

```bash
uv run python bench/run_bench.py -n 5 --workdir /tmp/legbench
uv run python bench/report.py
```

This costs real API credits (40 agent sessions at the default settings) and is
deliberately excluded from CI.

## Results: RETRACTED (2026-08-15)

**The n=5 run published earlier is withdrawn. It measured nothing, because of
three defects in the harness and fixture - all ours.**

The raw numbers stay in `bench/results/` and in git history. What is withdrawn
is any inference from them, in either direction.

### Why it was invalid

**1. The task did not require memory.** Session 1 fixes `sync/worker.py` with
`BEGIN IMMEDIATE`. Session 2 then opens a repo where that fix is sitting in the
sibling file. An agent can simply read `worker.py` and copy the pattern - no
memory needed. We built a memory benchmark in which the codebase *is* the
memory, so the baseline was never actually memory-less.

**2. `repeated_failure` was a false positive in every trial of both arms.**
`DEAD_END_PATTERNS` included `busy_timeout` and `BUSY_TIMEOUT_MS`, which are
present in the fixture's own `sync/db.py`. Any agent that read that file
matched the pattern. The reported "5/5 repeated failures in both arms" was
detecting agents *reading source code*, not agents repeating mistakes.

**3. (Corrected 2026-08-20.)** We first reported that the hook arm never fired
the hook. That was wrong - our detection searched only *assistant* transcript
events, while hook injections arrive as user-side context. The `.surfaced-*`
cache files in both trial repos prove the hook fired. Verified independently:
`.claude/settings.json` in a repo DOES activate PreToolUse hooks under headless
`claude -p`, including with `--strict-mcp-config`, and in a clean single-file
test the injected memory visibly shaped the answer. The hook arm's numbers
remain uninterpretable anyway, because of defect 1.

### What survives

Only these, and they are weak:

- Token and cost totals were really measured. In this (invalid) task shape,
  legendary cost more than baseline. That says nothing about tasks where memory
  is actually required.
- Agents did call `recall` and `remember` unprompted, from tool descriptions
  alone. Delivery via MCP works.
- The documented hook setup works: `.claude/settings.json` activates the
  PreToolUse hook in headless mode (initially reported otherwise; corrected
  above).

### What a valid benchmark requires

1. **Knowledge that cannot be recovered from the repo.** The insight must exist
   only in the earlier session - e.g. an approach that was tried and reverted,
   leaving no trace in the code, or an external constraint discovered at
   runtime.
2. **Dead-end detection that cannot match pre-existing source.** Patterns must
   be checked against a diff of what the agent *wrote*, and must not appear in
   the fixture to begin with.
3. **Verification that each arm's configuration actually activated**, asserted
   before trials count.

Until those exist, this project makes **no performance claim**.
